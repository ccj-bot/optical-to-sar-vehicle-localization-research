"""Small one-sided bright-band annotation margin; source/v2 remain immutable."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,copy,hashlib,json,os,shutil,subprocess,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import cv2

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'output/car_central_static_repair_20261102'
OUT=ROOT/'output/car_bright_band_margin_20261102'
PKG=ROOT/'output/car_data_contract_r35_20261030'
sys.path.insert(0,str(PKG/'runtime'))
from car_data_contract import CarDataset
from car_data_contract.geometry import native_corners

MARGIN=6.0
COLORS={'002':'#ffff4f','003':'#ef7cfa','005':'#35f7b1'}
KEYS=[358,400,420,440,470,494]
FONT='C:/Windows/Fonts/msyh.ttc'

def font(n=18):return ImageFont.truetype(FONT,n)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def corners(b):return native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']))

def expanded(b):
    theta=np.deg2rad(b['rotation_deg']);c,s=np.cos(theta),np.sin(theta)
    if b['height']>=b['width']:
        axis=np.array([-s,c]);dim='height';edge=[2,3];opposite=[0,1]
    else:
        axis=np.array([c,s]);dim='width';edge=[1,2];opposite=[0,3]
    if axis[1]<=0:raise ValueError('Review bright-band direction explicitly; do not guess signed axis')
    out=dict(b);out[dim]+=MARGIN;out['cx']+=float(axis[0]*MARGIN/2);out['cy']+=float(axis[1]*MARGIN/2)
    return out,axis,edge,opposite

def draw(d,b,col,label=None,dashed=True):
    cs=corners(b)
    for a,z in zip(cs,np.roll(cs,-1,axis=0)):
        length=np.linalg.norm(z-a)
        if dashed:
            for p in np.arange(0,length,9):d.line((tuple(a+(z-a)*p/length),tuple(a+(z-a)*min(p+5,length)/length)),fill=col,width=2)
        else:d.line((tuple(a),tuple(z)),fill=col,width=2)
    if label:d.text((b['cx']-14,b['cy']-10),label,font=font(17),fill=col,stroke_width=1,stroke_fill='#102434')

def main(preview=False):
    OUT.mkdir(parents=True,exist_ok=True)
    if not preview and (OUT/'ANNOTATIONS.json').exists():raise FileExistsError('This revision exists; preserve it')
    base=json.loads((BASE/'ANNOTATIONS.json').read_text(encoding='utf-8'));rows=[];max_opposite=0.;max_edge_error=0.
    for r in base['records']:
        nr=copy.deepcopy(r);old=r['sar_box'];new,axis,edge,opposite=expanded(old);a,z=corners(old),corners(new)
        max_opposite=max(max_opposite,float(np.max(np.abs(z[opposite]-a[opposite]))))
        max_edge_error=max(max_edge_error,float(np.max(np.abs(z[edge]-a[edge]-MARGIN*axis))))
        nr.update(sar_box=new,base_sar_box=old,
            annotation_author='CODEX_ASSISTANT_USER_REQUESTED_BOUNDARY_MARGIN',
            source_user_confirmed_this_frame=r['user_confirmed_this_frame'],user_confirmed_this_frame=False,
            frame_role='USER_REQUESTED_MARGIN_ON_V2',
            extent_source='V2_OPPOSITE_EDGE_AND_CROSS_AXIS_FIXED_BRIGHT_BAND_EDGE_PLUS_6PX',
            position_and_axis_source='V2_NAVIGATION_RETAINED_BOX_CENTER_REPARAMETERIZED_FOR_ONE_SIDED_MARGIN',
            review_state='MARGIN_REVISION_PENDING_VISUAL_SPOTCHECK',
            label_semantics='APPROXIMATE_BODY_RANGE_WITH_BRIGHT_BAND_MARGIN_NOT_PHYSICAL_FRONT_BACK',
            boundary_visibility='BRIGHT_BAND_SIDE_PADDED_FAR_BOUNDARY_INHERITED',
            margin_adjustment={'native_pixels':MARGIN,'axis_xy':axis.tolist(),'side':'BRIGHT_BAND_POSITIVE_IMAGE_Y_END','opposite_edge_fixed':True,'user_requested':True,'exact_margin_user_confirmed':False})
        rows.append(nr)
    data=CarDataset(PKG,view='review');by={f:[r for r in rows if r['sar_frame']==f] for f in range(358,495)}
    raw_cache={}
    def raw(f):
        if f not in raw_cache:raw_cache[f]=Image.fromarray(data.image('SAR',f))
        return raw_cache[f].copy()
    def render(f,version,footer=False):
        im=raw(f);d=ImageDraw.Draw(im)
        for r in by[f]:draw(d,r['sar_box'] if version==3 else r['base_sar_box'],COLORS[r['subject_id']],r['subject_id'])
        if not footer:return im
        canvas=Image.new('RGB',(1024,660),'#102637');canvas.paste(im,(0,0));d=ImageDraw.Draw(canvas)
        d.text((14,600),f'SAR {f} | '+('v3 亮带侧外放6px' if version==3 else 'v2 原边界'),font=font(21),fill='white')
        d.text((14,633),'002 白色SUV   003 灰色轿车   005 橙色车  |  近似整体范围',font=font(16),fill='#dae7ee')
        return canvas
    def detail(f):
        xs=[r['base_sar_box']['cx'] for r in by[f]];left=round(np.mean(xs))-200;crop=(left,145,left+400,465)
        panel=Image.new('RGB',(800,382),'#edf3f7');d=ImageDraw.Draw(panel)
        for i,v in enumerate([2,3]):
            im=render(f,v);di=ImageDraw.Draw(im)
            if v==3:
                for r in by[f]:
                    _,_,edge,_=expanded(r['base_sar_box']);oldc=corners(r['base_sar_box']);di.line((tuple(oldc[edge[0]]),tuple(oldc[edge[1]])),fill='#aebbc5',width=1)
            panel.paste(im.crop(crop),(i*400,36));d.text((i*400+10,5),f'SAR{f} | '+('v2 原边界' if v==2 else 'v3 亮带侧 +6px'),font=font(17),fill='#173246')
        d.text((10,359),'右图灰线：原亮带端边界；彩线向外移6px；另一端保持原位',font=font(13),fill='#314d60')
        return panel
    (OUT/'keyframes').mkdir(exist_ok=True)
    for f in KEYS:detail(f).save(OUT/'keyframes'/f'COMPARE_{f}.png')
    detail(494).save(OUT/'LAST_FRAME_COMPARE.png')
    if preview:
        print(json.dumps({'preview_frames':KEYS,'margin_px':MARGIN,'out':str(OUT)},ensure_ascii=False));return
    checks=[]
    def check(name,ok,**extra):
        checks.append({'check':name,'passed':bool(ok),**extra})
        if not ok:raise RuntimeError(checks[-1])
    check('Opposite edge unchanged in411 boxes',max_opposite<1e-9,max_abs_change_px=max_opposite)
    check('Bright-band edge moves exactly6px along long axis',max_edge_error<1e-9,max_abs_error_px=max_edge_error)
    check('All137 frames for each of three objects',len(rows)==411 and all(sorted(r['sar_frame'] for r in rows if r['subject_id']==s)==list(range(358,495)) for s in COLORS))
    check('Source confirmed labels not promoted to revised geometry',all(not r['user_confirmed_this_frame'] for r in rows))
    ann={k:copy.deepcopy(v) for k,v in base.items() if k not in ['records','review_record','method','extent_limit']}
    ann.update(schema='CENTRAL_STATIC_CAR_BRIGHT_BAND_MARGIN_V3',created=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        status='USER_REQUESTED_MARGIN_REVISION_FOR_REVIEW',source_annotation=str(BASE/'ANNOTATIONS.json'),source_annotation_sha256=sha(BASE/'ANNOTATIONS.json'),
        user_instruction='不一定是车头，但是亮带可以再往前一点点包住',
        method='V2 motion/axis retained; bright-band end extended6 native pixels; opposite edge and cross-axis width fixed.',
        extent_limit='Margin is an annotation allowance, not newly measured vehicle size. Far boundary remains inherited. Physical front/back unresolved.',records=rows)
    dump('ANNOTATIONS.json',ann);dump('KEYFRAME_REVISIONS.json',[r for r in rows if r['sar_frame'] in KEYS])
    for p in ['sar_frames','compare_frames','verification']:(OUT/p).mkdir(exist_ok=True)
    for f in range(358,495):
        new=render(f,3,True);new.save(OUT/'sar_frames'/f'{f:06d}.jpg',quality=93)
        comp=Image.new('RGB',(2048,660));comp.paste(render(f,2,True),(0,0));comp.paste(new,(1024,0));comp.save(OUT/'compare_frames'/f'{f:06d}.jpg',quality=93)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    videos=[]
    for folder,name in [('sar_frames','CORRECTED_SAR.mp4'),('compare_frames','BEFORE_AFTER.mp4')]:
        dest=OUT/name
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-n','-framerate','10','-start_number','358','-i',str(OUT/folder/'%06d.jpg'),'-frames:v','137','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
        cap=cv2.VideoCapture(str(dest));n=0
        while True:
            ok,im=cap.read()
            if not ok:break
            if n==136:Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)).save(OUT/'verification'/f'{dest.stem}_494.jpg',quality=95)
            n+=1
        cap.release();check(name+'137frames',n==137);videos.append({'name':name,'frame_count':n,'fps':10,'duration':n/10,'sha256':sha(dest)})
    src_manifest=json.loads((BASE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    check('All137 SAR source hashes preserved',all(sha(r['path'])==r['sha256'] for r in src_manifest['sar']))
    baseline_manifest=json.loads((BASE/'DELIVERY_MANIFEST.json').read_text(encoding='utf-8'))
    check('All344 v2 artifacts unchanged',all(sha(r['path'])==r['sha256'] for r in baseline_manifest['files']),count=len(baseline_manifest['files']))
    dump('VERIFICATION.json',{'status':'PASS_GEOMETRY_MEDIA_PRESERVATION','checks':checks,'videos':videos,'meaning':'Geometry consistency, file preservation and video decoding; not annotation accuracy.'})
    dump('SOURCE_MANIFEST.json',src_manifest)
    # Existing viewer controls are reused; this is a separate file and independent UI.
    html=(BASE/'index.html').read_text(encoding='utf-8')
    html=html.replace('修订 v2','亮带边界 v3')
    html=html.replace('已修订连续位置与方向，并逐帧检查三车区域。虚线框的长宽沿用358人工参考，弱远端尚未独立重测。','沿用v2连续轨迹，将亮带一侧外放6个原生像素，让亮带留有余量。另一端、方向与横向宽度保持。')
    html=html.replace('左为旧版，右为修订版。原数据、358人工框和旧结果保留。','左为v2，右为v3。只外放亮带侧边界；原数据、358人工框和v2保留。')
    html=html.replace('keyframes/COMPARE_440.png','LAST_FRAME_COMPARE.png').replace('16个关键时相','6个核查时相')
    (OUT/'index.html').write_text(html,encoding='utf-8')
    note='''# R35亮带侧微调 v3

2026-11-02。按用户澄清，将亮带一侧稍向外放，让响应被包住，不将这一端命名为物理车头。

[逐帧查看](index.html) · [v2/v3完整对照视频](BEFORE_AFTER.mp4) · [末帧近看](LAST_FRAME_COMPARE.png) · [逐帧标注](ANNOTATIONS.json)

三车002/003/005、SAR358–494，共137帧411条记录。亮带端沿长轴外放6个原生像素，另一端固定。短轴宽度和方向不变；中心坐标因单侧延长而沿轴移动3像素，是框参数变化，不是重新估计目标位置。源358原人工框保存在v2与源文件中；v3的358也作为边界修订另存，不冒充原人工确认。

6px是为亮带留余量的标注选择，不是实测车长增长。弱远端仍沿用原范围，未建立物理车头/车尾或独立整车真值。

技术检查见[VERIFICATION](VERIFICATION.json)：全部411个框对侧边界保持、亮带端外移6px；全部137源帧及344个v2交付文件哈希保持；两视频各137帧、10fps慢放。视觉核查另见[VISUAL_REVIEW](VISUAL_REVIEW.md)。

源程序：tasks/car_bright_band_margin_20261102/build.py；解释器 python -X utf8 -B。未重跑跟踪、未训练，已有原图和旧标注保持。
'''
    (OUT/'START_HERE.md').write_text(note,encoding='utf-8')
    print(json.dumps({'rows':411,'frames':137,'margin_px':MARGIN,'checks':len(checks),'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');main(ap.parse_args().preview)
