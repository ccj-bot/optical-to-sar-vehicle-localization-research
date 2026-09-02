from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_local_boundary_observability_20260902"
OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
LOG = WORKSPACE / "logs" / "20260902_r02_local_boundary_observability.md"
PACK = OUT / "R02_LOCAL_BOUNDARY_OBSERVABILITY_REVIEW_PACK_20260902.zip"
PACK_MANIFEST = OUT / "REVIEW_PACK_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def arcname(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


def main() -> None:
    paths = sorted(path for path in TASK.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    paths += [LOG]
    paths += sorted(
        path
        for path in OUT.rglob("*")
        if path.is_file() and path not in {PACK, PACK_MANIFEST}
    )
    paths = sorted(set(paths), key=lambda path: arcname(path))
    manifest = {
        "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_REVIEW_PACK_MANIFEST_V1",
        "pack_filename": PACK.name,
        "raw_manual_jsonl_included": False,
        "file_count": len(paths),
        "files": [
            {"workspace_relative_path": arcname(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in paths
        ],
    }
    PACK_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths.append(PACK_MANIFEST)
    with zipfile.ZipFile(PACK, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(paths, key=lambda item: arcname(item)):
            info = zipfile.ZipInfo(arcname(path), date_time=(2026, 9, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    print(PACK)
    print(f"bytes={PACK.stat().st_size}")
    print(f"sha256={sha256(PACK)}")


if __name__ == "__main__":
    main()
