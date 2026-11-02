"""Run PERSON legacy, recovery or sequence localization with explicit inputs."""
import argparse
import json
import sys
from pathlib import Path

if __package__ in [None, '']:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from threadpoolctl import threadpool_limits
from person_localizer import __version__
from person_localizer.pipeline import Scene, sha, dump


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=__version__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--scene', type=Path)
    inputs.add_argument('--manifest', type=Path, help='explicit sequence input manifest')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--config', type=Path, help='legacy/recovery config; sequence uses manifest.config')
    parser.add_argument('--gate-only', action='store_true', help='optical eligibility only; no SAR decoding or fitting')
    parser.add_argument('--engine', choices=['auto','legacy','recovery','sequence'], default='auto')
    parser.add_argument('--feedback', action='store_true', help='use explicitly declared sequence terminal feedback')
    args = parser.parse_args(argv)
    spec = read(args.scene) if args.scene else None
    engine = ('sequence' if args.manifest else spec.get('person_engine','legacy')) if args.engine=='auto' else args.engine
    if engine not in {'legacy','recovery','sequence'}:
        parser.error('scene.person_engine must be legacy, recovery or sequence')
    if args.manifest and engine!='sequence': parser.error('--manifest requires sequence engine')
    if args.feedback and engine!='sequence': parser.error('--feedback is only valid for sequence')
    if args.feedback and args.gate_only: parser.error('--feedback cannot be combined with --gate-only')
    cv2.setNumThreads(4)
    threadpool_limits(4)
    cv2.setRNGSeed(20261027 if engine=='sequence' else 20261026)
    if engine=='sequence':
        if args.config: parser.error('sequence config belongs in manifest.config')
        manifest = args.manifest
        if manifest is None:
            if not spec.get('sequence_manifest'): parser.error('sequence scene requires sequence_manifest or use --manifest')
            manifest = Path(spec['sequence_manifest'])
            if not manifest.is_absolute(): manifest=args.scene.parent/manifest
        data = read(manifest)
        if args.feedback and not data.get('terminal_feedback'): parser.error('manifest has no terminal_feedback')
        if spec is not None and spec.get('scene_id') != read(data['scene']).get('scene_id'):
            parser.error('sequence pointer and manifest scene_id differ')
        package = dict(version=__version__,engine=engine,input_manifest=str(manifest.resolve()),
            manifest_sha256=sha(manifest),config_sha256=sha(data['config']),scene_spec_sha256=sha(data['scene']),
            feedback_conditioned=bool(args.feedback))
        if args.gate_only:
            scene = Scene(read(data['scene']),read(data['config']),args.output)
            scene.filter_inputs()
            dump(scene.out/'GATE_ONLY.json',dict(SAR_pixels_decoded=False,candidate_fitting_executed=False))
        else:
            from person_localizer.sequence_runner import execute
            execute(manifest,args.output,feedback=args.feedback)
        dump(args.output/'PACKAGE.json',package)
        return
    config_path = args.config
    if config_path is None and spec.get('person_config'):
        config_path=Path(spec['person_config'])
        if not config_path.is_absolute():config_path=args.scene.parent/config_path
    config_path = config_path or Path(__file__).with_name('config.json')
    config = read(config_path)
    required = {'scene_id','sar_video','optical_csv','native_width','native_height','sar_fps','optical_fps','queries'}
    if not required <= set(spec): parser.error(f'Missing scene keys: {sorted(required-set(spec))}')
    scene = Scene(spec,config,args.output)
    dump(scene.out/'PACKAGE.json',dict(version=__version__,engine=engine,
        config_sha256=sha(config_path),scene_spec_sha256=sha(args.scene),
        initialization_geometry_scope=config.get('initialization_geometry_scope','whole_track')))
    if args.gate_only:
        scene.filter_inputs()
        dump(scene.out/'GATE_ONLY.json',dict(SAR_pixels_decoded=False,candidate_fitting_executed=False))
        return
    if engine=='recovery':
        from person_localizer.recovery_runner import run
        run(scene,spec.get('response_recovery',{}))
    else:
        scene.run()


if __name__=='__main__':
    main()
