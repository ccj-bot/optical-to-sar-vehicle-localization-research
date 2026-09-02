from __future__ import annotations

import argparse
import json
import mimetypes
import socket
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2


TASK = Path(__file__).resolve().parent
WEB = TASK / "web_simple"
sys.path.insert(0, str(TASK))

from r02_static_scene_annotator import (  # noqa: E402
    DEFAULT_BATCH,
    DEFAULT_USER_DIR,
    LABELS,
    AnnotationStore,
    atomic_write_text,
    read_batch,
    read_bgr,
    utc_now,
)


LABEL_BY_OBJECT_TYPE = {label.object_type: label for label in LABELS.values()}


class BrowserAnnotationService:
    def __init__(self, batch_path: Path, output_dir: Path) -> None:
        self.batch_path = batch_path
        self.batch = read_batch(batch_path)
        self.by_batch_index = {int(row["batch_index"]): row for row in self.batch}
        self.store = AnnotationStore(output_dir, self.batch)
        self.lock = threading.RLock()
        self.session = self._load_session()
        self.image_shapes: dict[str, tuple[int, int]] = {}

    def _load_session(self) -> dict[str, object]:
        default = {
            "schema": "R02_STATIC_SCENE_BROWSER_SESSION_V2",
            "current_index": 0,
            "confidence_state": "CONFIDENT",
            "hints_enabled": False,
            "skipped_batch_indices": [],
            "last_saved_at": utc_now(),
        }
        if not self.store.state_path.exists():
            return default
        try:
            existing = json.loads(self.store.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return default
        default["current_index"] = min(max(int(existing.get("current_index", 0)), 0), len(self.batch) - 1)
        default["confidence_state"] = str(existing.get("confidence_state", "CONFIDENT"))
        default["hints_enabled"] = bool(existing.get("hints_enabled", False))
        default["skipped_batch_indices"] = sorted({int(item) for item in existing.get("skipped_batch_indices", [])})
        return default

    @property
    def skipped(self) -> set[int]:
        return {int(item) for item in self.session.get("skipped_batch_indices", [])}

    def save_session(self) -> None:
        self.session["last_saved_at"] = utc_now()
        atomic_write_text(self.store.state_path, json.dumps(self.session, ensure_ascii=False, indent=2))

    def public_batch(self) -> list[dict[str, object]]:
        keep = [
            "batch_index",
            "run_id",
            "optical_frame_index",
            "optical_timestamp_ms",
            "sar_frame_index",
            "sar_timestamp_ms",
            "nominal_timestamp_residual_ms",
            "sync_status",
            "selection_reason",
            "bracket_id",
            "seed_role",
            "annotation_scope",
            "visual_difficulty",
            "notes",
        ]
        return [{key: row.get(key, "") for key in keep} for row in self.batch]

    @property
    def workflow_mode(self) -> str:
        scopes = {str(row.get("annotation_scope", "FULL_STATIC_SCENE")) for row in self.batch}
        return "SAR_BOUNDARY_ONLY" if scopes == {"SAR_BOUNDARY_ONLY"} else "FULL_STATIC_SCENE"

    def state_payload(self) -> dict[str, object]:
        with self.lock:
            return {
                "schema": "R02_STATIC_SCENE_BROWSER_STATE_V2",
                "workflow_mode": self.workflow_mode,
                "guided_boundary_order": (
                    ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
                    if self.workflow_mode == "SAR_BOUNDARY_ONLY"
                    else ["OPT_BOUNDARY_NEAR", "OPT_BOUNDARY_FAR", "SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
                ),
                "batch": self.public_batch(),
                "annotations": list(self.store.latest.values()),
                "session": self.session,
                "labels": [
                    {
                        "key": label.key,
                        "modality": label.modality,
                        "object_id": label.object_id,
                        "object_type": label.object_type,
                        "geometry_type": label.geometry_type,
                        "short_name": label.short_name,
                        "color_bgr": list(label.color),
                    }
                    for label in LABELS.values()
                ],
                "output_files": {
                    "events": str(self.store.events_path),
                    "summary": str(self.store.summary_path),
                    "progress": str(self.store.progress_path),
                    "coverage": str(self.store.coverage_path),
                },
                "automatic_hints_are_identity_authority": False,
                "person_gt": False,
            }

    def image_path(self, batch_index: int, modality: str) -> Path:
        row = self.by_batch_index[batch_index]
        key = "optical_image_path" if modality == "OPTICAL" else "sar_image_path"
        return Path(str(row[key]))

    def shape(self, batch_index: int, modality: str) -> tuple[int, int]:
        path = self.image_path(batch_index, modality)
        key = str(path)
        if key not in self.image_shapes:
            image = read_bgr(path)
            self.image_shapes[key] = (int(image.shape[1]), int(image.shape[0]))
        return self.image_shapes[key]

    def validate_points(self, batch_index: int, modality: str, points: list[list[float]]) -> list[list[float]]:
        width, height = self.shape(batch_index, modality)
        validated = []
        for item in points:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("Each point must be [x, y]")
            x, y = float(item[0]), float(item[1])
            if not (0.0 <= x < width and 0.0 <= y < height):
                raise ValueError(f"Point outside {modality} image: {(x, y)} vs {(width, height)}")
            validated.append([x, y])
        return validated

    def save_annotation(self, payload: dict[str, object]) -> dict[str, object]:
        with self.lock:
            batch_index = int(payload["batch_index"])
            object_type = str(payload["object_type"])
            label = LABEL_BY_OBJECT_TYPE[object_type]
            batch_row = self.by_batch_index[batch_index]
            points = self.validate_points(batch_index, label.modality, list(payload.get("points", [])))
            confidence = str(payload.get("confidence_state", "CONFIDENT"))
            geometry_status = str(payload.get("geometry_status", "DRAFT"))
            visibility = str(payload.get("visibility_state", "VISIBLE_OR_GEOMETRY_PROVIDED"))
            if geometry_status == "COMPLETE" and visibility == "VISIBLE_OR_GEOMETRY_PROVIDED":
                if label.geometry_type == "polyline" and len(points) < 2:
                    raise ValueError("A completed polyline needs at least two points")
                if label.geometry_type == "point" and len(points) != 1:
                    raise ValueError("A visible point annotation needs exactly one point")
            record = self.store.upsert(
                batch_row,
                label,
                points,
                confidence,
                geometry_status,
                visibility,
                str(payload.get("user_comment", "")),
            )
            skipped = self.skipped
            skipped.discard(batch_index)
            self.session["skipped_batch_indices"] = sorted(skipped)
            self.store.write_views(skipped)
            self.save_session()
            return record

    def delete_annotation(self, payload: dict[str, object]) -> None:
        with self.lock:
            batch_index = int(payload["batch_index"])
            label = LABEL_BY_OBJECT_TYPE[str(payload["object_type"])]
            self.store.delete(self.by_batch_index[batch_index], label)
            self.store.write_views(self.skipped)
            self.save_session()

    def update_session(self, payload: dict[str, object]) -> dict[str, object]:
        with self.lock:
            if "current_index" in payload:
                self.session["current_index"] = min(max(int(payload["current_index"]), 0), len(self.batch) - 1)
            if "confidence_state" in payload:
                self.session["confidence_state"] = str(payload["confidence_state"])
            if "hints_enabled" in payload:
                self.session["hints_enabled"] = bool(payload["hints_enabled"])
            if "skip_batch_index" in payload:
                skipped = self.skipped
                skipped.add(int(payload["skip_batch_index"]))
                self.session["skipped_batch_indices"] = sorted(skipped)
                self.store.write_views(skipped)
            self.save_session()
            return self.session


class Handler(BaseHTTPRequestHandler):
    server_version = "R02ManualScene/2.0"

    @property
    def service(self) -> BrowserAnnotationService:
        return self.server.service  # type: ignore[attr-defined]

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[R02 annotator] {self.address_string()} {format_string % args}")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 2_000_000:
            raise ValueError("Request is too large")
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "service": "R02_MANUAL_STATIC_SCENE_BROWSER_V2"})
            return
        if parsed.path == "/api/state":
            self.send_json(self.service.state_payload())
            return
        if parsed.path == "/api/image":
            try:
                query = urllib.parse.parse_qs(parsed.query)
                batch_index = int(query["batch_index"][0])
                modality = query["modality"][0].upper()
                if modality not in {"OPTICAL", "SAR"}:
                    raise ValueError("Invalid modality")
                path = self.service.image_path(batch_index, modality)
                body = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "private, max-age=3600")
                self.end_headers()
                self.wfile.write(body)
            except (KeyError, ValueError, OSError) as error:
                self.send_error_json(str(error), HTTPStatus.NOT_FOUND)
            return
        self.send_static(parsed.path)

    def send_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (WEB / relative).resolve()
        if not str(candidate).startswith(str(WEB.resolve())) or not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/save":
                record = self.service.save_annotation(payload)
                self.send_json({"ok": True, "record": record, "state": self.service.state_payload()})
                return
            if parsed.path == "/api/delete":
                self.service.delete_annotation(payload)
                self.send_json({"ok": True, "state": self.service.state_payload()})
                return
            if parsed.path == "/api/session":
                session = self.service.update_session(payload)
                self.send_json({"ok": True, "session": session})
                return
            if parsed.path == "/api/shutdown":
                self.send_json({"ok": True, "message": "Saved. Server is shutting down."})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            self.send_error_json("Unknown API endpoint", HTTPStatus.NOT_FOUND)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error))


class AnnotationHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], service: BrowserAnnotationService) -> None:
        super().__init__(address, Handler)
        self.service = service


def choose_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as stream:
            if stream.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local port in the annotation range")


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def smoke_test(batch_path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="r02_browser_annotation_smoke_") as temporary:
        service = BrowserAnnotationService(batch_path, Path(temporary))
        server = AnnotationHTTPServer(("127.0.0.1", 0), service)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        with urllib.request.urlopen(base + "/api/health", timeout=10) as response:
            health = json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(base + "/api/state", timeout=10) as response:
            state = json.loads(response.read().decode("utf-8"))
        test_modality = "SAR" if service.workflow_mode == "SAR_BOUNDARY_ONLY" else "OPTICAL"
        test_object_type = "SAR_BOUNDARY_NEAR" if service.workflow_mode == "SAR_BOUNDARY_ONLY" else "OPT_BOUNDARY_NEAR"
        with urllib.request.urlopen(base + f"/api/image?batch_index=1&modality={test_modality}", timeout=10) as response:
            image_bytes = response.read()
        saved = post_json(
            base + "/api/save",
            {
                "batch_index": 1,
                "object_type": test_object_type,
                "points": [[100.0, 200.0], [300.0, 205.0]],
                "confidence_state": "CONFIDENT",
                "geometry_status": "COMPLETE",
                "visibility_state": "VISIBLE_OR_GEOMETRY_PROVIDED",
            },
        )
        shutdown = post_json(base + "/api/shutdown", {})
        thread.join(timeout=10)
        event_lines = service.store.events_path.read_text(encoding="utf-8").splitlines()
        return {
            "status": "PASS" if health.get("ok") and saved.get("ok") and shutdown.get("ok") else "FAIL",
            "workflow_mode": state.get("workflow_mode"),
            "guided_boundary_order": state.get("guided_boundary_order"),
            "batch_count": len(state["batch"]),
            "image_bytes": len(image_bytes),
            "event_lines": len(event_lines),
            "server_stopped": not thread.is_alive(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple precise browser annotator for R02ZF")
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_USER_DIR)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.smoke_test:
        print(json.dumps(smoke_test(args.batch), ensure_ascii=False, indent=2))
        return
    port = choose_port(args.port)
    service = BrowserAnnotationService(args.batch, args.output_dir)
    server = AnnotationHTTPServer(("127.0.0.1", port), service)
    url = f"http://127.0.0.1:{port}/"
    print(f"R02 annotation tool: {url}")
    print(f"Manual annotations: {service.store.events_path}")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.store.write_views(service.skipped)
        service.save_session()
        server.server_close()


if __name__ == "__main__":
    main()
