"""Bind the finished normalized package and its exact builder/reader sources."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from normalize import ROOT,OUT,TASK,sha,read_json,dump_json

def main(out=OUT):
    out=Path(out)
    if (out/'RELEASE_SEAL.json').exists():raise FileExistsError('Existing seal is immutable; create a new package version')
    v=read_json(out/'VERIFICATION.json');assert v['status']=='PASS_DATA_INTEGRITY_AND_SEMANTIC_GUARDS'
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='RELEASE_SEAL.json'}
    sources={str(p):sha(p) for folder in [TASK,ROOT/'tools/car_data_contract'] for p in folder.glob('*.py')}
    dump_json(out/'RELEASE_SEAL.json',{'created':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
      'scope':'DATA_REPRESENTATION_AND_PROVENANCE_NOT_SCIENTIFIC_LABEL_ACCEPTANCE','files':files,'builder_and_reader_sources':sources,
      'source_manifest_sha256':sha(out/'SOURCE_MANIFEST.json'),'validation_sha256':sha(out/'VERIFICATION.json')})
    print(f'SEALED {len(files)} package files; {len(sources)} source files',flush=True)
if __name__=='__main__':main()
