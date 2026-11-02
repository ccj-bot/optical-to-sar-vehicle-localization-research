"""Read-only source inspection and separately versioned R35 annotation repair."""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/car_central_static_repair_20261102'
PKG = ROOT / 'output/car_data_contract_r35_20261030'
OLD = ROOT / 'output/car_central_static_annotation_20261101'
sys.path.insert(0, str(PKG / 'runtime'))
from car_data_contract import CarDataset
from car_data_contract.geometry import native_corners

FONT = 'C:/Windows/Fonts/msyh.ttc'
COLORS = {'002':'#ffff4f','003':'#ef7cfa','005':'#35f7b1'}
NAMES = {'002':'白色SUV','003':'灰色轿车','005':'橙色车'}

def font(n=18):
    return ImageFont.truetype(FONT,n)

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def source():
    return CarDataset(PKG,view='review')

def raw_sheet(frames, crop=(200,160,820,520), name=None):
    data=source();w,h=crop[2]-crop[0],crop[3]-crop[1]
    sheet=Image.new('RGB',(2*w,((len(frames)+1)//2)*(h+46)),'#eaf0f4')
    d=ImageDraw.Draw(sheet)
    for j,f in enumerate(frames):
        x,y=(j%2)*w,(j//2)*(h+46)
        im=Image.fromarray(data.image('SAR',f)).crop(crop)
        sheet.paste(im,(x,y+46))
        d.text((x+10,y+4),f'SAR {f} | 原图裁剪 x{crop[0]}–{crop[2]} y{crop[1]}–{crop[3]}',font=font(16),fill='#142532')
        for xx in range(((crop[0]+49)//50)*50,crop[2],50):
            px=x+xx-crop[0]
            d.line((px,y+32,px,y+45),fill='#142532',width=1)
            d.text((px+2,y+27),str(xx),font=font(11),fill='#142532')
    path=OUT/'reading'/(name or ('raw_'+'_'.join(map(str,frames))+'.png'))
    path.parent.mkdir(parents=True,exist_ok=True);sheet.save(path)
    return str(path)

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    data=source()
    frames=[358,370,380,390,400,410,420,430,440,450,460,470,480,486,490,494]
    paths=[raw_sheet(frames[k:k+4]) for k in range(0,len(frames),4)]
    manifest=[]
    for f in range(358,495):
        r=data.frame('SAR',f)
        data.image('SAR',f)
        manifest.append({'frame':f,'path':r['image_path'],'sha256':r['image_sha256']})
    dump(OUT/'SOURCE_MANIFEST.json',{'sar':manifest,'panels':paths,'transform':'Exact native RGB crop; no intensity adjustment, no warp, no denoising.'})
    print(json.dumps({'panels':paths,'source_frames_verified':len(manifest)},ensure_ascii=False))
    for f in [358,400,420,440,460,480,494]:
        print(f,data.transform(f,transform_id='offline_public_translation_v2')['public_delta'])

def object_sheet(subject,frames):
    data=source();old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records']
    rows={r['sar_frame']:r for r in old if r['subject_id']==subject}
    w,h=280,270
    out=Image.new('RGB',(2*w,((len(frames)+1)//2)*(h+46)),'#eef2f4');d=ImageDraw.Draw(out)
    for i,f in enumerate(frames):
        box=rows[f]['sar_box'];left=int(round(box['cx']))-140;top=int(round(box['cy']))-135
        im=Image.fromarray(data.image('SAR',f)).crop((left,top,left+w,top+h));di=ImageDraw.Draw(im)
        if f==358:
            corners=native_corners(*(box[k] for k in ['cx','cy','width','height','rotation_deg']))-np.array([left,top])
            di.line([tuple(p) for p in np.vstack([corners,corners[:1]])],fill=COLORS[subject],width=1)
        for xx in range(((left+24)//25)*25,left+w,25):
            di.text((xx-left+1,2),str(xx),font=font(10),fill='white',stroke_width=1,stroke_fill='#132231')
            di.line((xx-left,15,xx-left,21),fill='white')
        for yy in range(((top+24)//25)*25,top+h,25):
            di.text((1,yy-top),str(yy),font=font(10),fill='white',stroke_width=1,stroke_fill='#132231')
            di.line((24,yy-top,30,yy-top),fill='white')
        x,y=(i%2)*w,(i//2)*(h+46);out.paste(im,(x,y+46))
        d.text((x+8,y+5),f'{subject} | SAR {f} | x{left} y{top}',font=font(17),fill='#172b39')
        d.text((x+8,y+26),'358原人工框；其余无框原图',font=font(12),fill='#172b39')
    path=OUT/'reading'/f'object_{subject}_{"_".join(map(str,frames))}.png';out.save(path);return str(path)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['prepare','sheet','object']);ap.add_argument('--subject',default='002');ap.add_argument('--frames',type=int,nargs='+');ap.add_argument('--crop',type=int,nargs=4,default=[200,160,820,520]);args=ap.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='sheet':print(raw_sheet(args.frames,tuple(args.crop)))
    elif args.command=='object':print(object_sheet(args.subject,args.frames))
