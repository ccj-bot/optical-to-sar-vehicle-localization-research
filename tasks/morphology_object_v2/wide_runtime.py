"""Single frozen native-SAR aperture. This process has no GT loader."""
import argparse,json,hashlib,sys
from pathlib import Path
import numpy as np
from PIL import Image
from object_core import build_object,PARAMETERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    freeze_path=Path(__file__).with_name('wide_freeze.json');freeze=json.loads(freeze_path.read_text());args.out.mkdir(parents=True,exist_ok=True)
    opens=[]
    def audit(event,data):
        if event=='open' and isinstance(data[0],(str,bytes)):opens.append(str(data[0]))
    sys.addaudithook(audit)
    source=args.raw_root/freeze['image'];rgb=np.array(Image.open(source));assert np.array_equal(rgb[:,:,0],rgb[:,:,1])
    x0,y0,x1,y1=freeze['observation_xyxy'];z=rgb[y0:y1,x0:x1,0].astype(float)
    obj,arr=build_object(z,freeze['id']);obj['full_field']['file']='wide_field.npz';obj['aperture']=freeze
    np.savez_compressed(args.out/'wide_field.npz',**arr)
    default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist()
    (args.out/'wide_object.json').write_text(json.dumps(obj,indent=2,default=default),encoding='utf-8')
    record=dict(freeze_sha256=hashlib.sha256(freeze_path.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                object_sha256=hashlib.sha256((args.out/'wide_object.json').read_bytes()).hexdigest(),parameters=PARAMETERS,
                decoded_shape=list(z.shape),runtime_file_opens=opens.copy(),uncertainty=obj['uncertainty'],runtime_gt_access=False)
    (args.out/'WIDE_RUNTIME_AUDIT.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('wide materialized',len(obj['nuclei']),len(obj['segments']),len(obj['relations']),obj['uncertainty'],flush=True)

if __name__=='__main__':main()
