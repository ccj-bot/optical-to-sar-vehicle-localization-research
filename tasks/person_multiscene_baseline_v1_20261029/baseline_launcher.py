"""Run a sealed PERSON scene profile using this bundle's frozen rc9 code."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys


BASE = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def local_path(relative):
    p = (BASE / relative).resolve()
    if not p.is_relative_to(BASE):
        raise ValueError(f'Bundle path escapes release: {relative}')
    return p


def verify_package():
    seal = read(BASE / 'RELEASE_SEAL.json')
    actual={p.relative_to(BASE).as_posix() for p in BASE.rglob('*')
        if p.is_file() and p.name!='RELEASE_SEAL.json' and '__pycache__' not in p.parts}
    if actual != set(seal['files']):
        raise RuntimeError('Frozen release inventory changed; additions or removals require a new version')
    for relative, expected in seal['files'].items():
        p = local_path(relative)
        if not p.is_file() or sha(p) != expected:
            raise RuntimeError(f'Frozen release file changed: {relative}')
    return seal


def verify_environment():
    recorded=read(BASE/'ENVIRONMENT.json')
    if sys.version.split()[0] != recorded['python_version'].split()[0]:
        raise RuntimeError('Python version differs from the frozen environment')
    for name, expected in recorded['packages'].items():
        if expected is not None and importlib.metadata.version(name) != expected:
            raise RuntimeError(f'Package version differs from baseline: {name} (expected {expected})')


def verify_external(scene, scope):
    checked = []
    for entry in read(BASE / 'EXTERNAL_DEPENDENCIES.json'):
        if scene is not None and scene not in entry['scenes']:
            continue
        if scope == 'gate' and entry['role'] not in {'runtime_optical_evidence'}:
            continue
        p = Path(entry['path'])
        if not p.is_file() or sha(p) != entry['sha256']:
            raise RuntimeError(f'External dependency missing or changed: {p}')
        checked.append(str(p))
    return checked


def expand(value):
    if isinstance(value, str) and value.startswith('bundle://'):
        return str(local_path(value[len('bundle://'):]))
    if isinstance(value, list):
        return [expand(x) for x in value]
    if isinstance(value, dict):
        return {expand(k): expand(v) for k, v in value.items()}
    return value


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', choices=['R01ZF','R04ZF','GM_RM017','R02ZF','R07ZF','R50ZF'])
    parser.add_argument('--output', type=Path, help='new run directory outside the frozen bundle')
    parser.add_argument('--list', action='store_true', help='list the six frozen profiles')
    parser.add_argument('--check', action='store_true', help='verify the bundle and external dependencies only')
    parser.add_argument('--gate-only', action='store_true', help='real optical-input check; no SAR inference')
    args = parser.parse_args(argv)
    if not (args.list or args.check or args.scene):
        parser.error('use --list, --check or --scene')
    if args.gate_only and (args.list or args.check):
        parser.error('--gate-only is a run mode')
    seal = verify_package()
    registry = read(BASE / 'BASELINE.json')
    if args.list:
        for p in registry['profiles']:
            print(f"{p['scene']:10s} {p['engine']:8s} SAR {p['frames'][0]}-{p['frames'][1]}  {p['status']}")
        return
    if args.check:
        verify_environment()
        checked = verify_external(args.scene, 'run')
        print(json.dumps(dict(status='PASS',release=registry['release_id'],package_files=len(seal['files']),
            external_files=len(checked),scope=args.scene or 'all6'),ensure_ascii=False))
        return
    if args.output is None:
        parser.error('--scene requires --output unless using --check')
    verify_environment()
    profile = next(x for x in registry['profiles'] if x['scene'] == args.scene)
    output = args.output.resolve()
    if output == BASE or output.is_relative_to(BASE):
        parser.error('run output must be outside the frozen release')
    if output.exists():
        parser.error('run output already exists; choose a new directory')
    checked = verify_external(args.scene, 'gate' if args.gate_only else 'run')
    output.mkdir(parents=True, exist_ok=False)
    generated = output / 'resolved_inputs'; generated.mkdir()
    cfg = expand(read(local_path(profile['config'])))
    spec = expand(read(local_path(profile['spec'])))
    cfg_path, spec_path = generated/'CONFIG.json', generated/'SCENE.json'
    write(cfg_path, cfg); write(spec_path, spec)
    command = [sys.executable,'-X','utf8','-B',str(BASE/'runtime/person_localizer/cli.py')]
    if profile['engine'] == 'sequence':
        m = expand(read(local_path(profile['manifest'])))
        m['scene'], m['config'] = str(spec_path), str(cfg_path)
        manifest_path = generated/'MANIFEST.json'; write(manifest_path,m)
        command += ['--manifest', str(manifest_path)]
    else:
        spec['person_engine'] = profile['engine']; spec['person_config'] = str(cfg_path)
        write(spec_path,spec)
        command += ['--scene',str(spec_path),'--config',str(cfg_path)]
    command += ['--output',str(output/'result')]
    if args.gate_only: command += ['--gate-only']
    receipt = dict(release=registry['release_id'],scene=args.scene,engine=profile['engine'],
        release_seal_sha256=sha(BASE/'RELEASE_SEAL.json'),frozen_runtime=str(BASE/'runtime/person_localizer'),
        external_dependencies_checked=checked,gate_only=bool(args.gate_only),command=command,
        baseline_frames=profile['frames'],reference_predictions_loaded_by_inference=False)
    write(output/'BASELINE_RUN.json',receipt)
    env = dict(os.environ); env['PYTHONDONTWRITEBYTECODE']='1'
    done = subprocess.run(command, cwd=output, env=env)
    receipt['returncode'] = done.returncode
    if done.returncode == 0:
        package = read(output/'result/PACKAGE.json')
        if package['engine'] != profile['engine']:
            raise RuntimeError('Resolved runtime engine does not match the frozen profile')
        receipt['actual_engine'] = package['engine']
    write(output/'BASELINE_RUN.json',receipt)
    raise SystemExit(done.returncode)


if __name__ == '__main__':
    main()
