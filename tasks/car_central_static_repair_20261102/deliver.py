"""Package actual visual review, provenance verification, and readable results."""
from review import *
from datetime import datetime
from zoneinfo import ZoneInfo
import os,shutil,subprocess
import cv2

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    data=source();ann=json.loads((OUT/'ANNOTATIONS.json').read_text(encoding='utf-8'));rows=ann['records']
    report=ROOT/'tasks/car_central_static_repair_20261102/VISUAL_REVIEW.md'
    review=json.loads((OUT/'SEQUENCE_REVIEW.json').read_text(encoding='utf-8'))
    for p in review['pages']:p['inspection_status']='ACTUALLY_OPENED_AND_VISUALLY_REVIEWED_BY_ASSISTANT';p['sha256']=sha(p['path'])
    review.update(status='ASSISTANT_VISUAL_REVIEW_COMPLETE_NOT_HUMAN_GROUND_TRUTH',notes=str(report),scope='137 native three-object crops inspected, plus raw/fullframe and optical context samples')
    dump(OUT/'SEQUENCE_REVIEW.json',review)
    for r in rows:
        if r['sar_frame']!=358:r['review_state']='ASSISTANT_VISUAL_REVIEWED_APPROXIMATE_BODY_RANGE'
    ann['status']='ASSISTANT_REVIEWED_REVISION_NOT_NEW_CONFIRMED_GT';ann['review_record']='SEQUENCE_REVIEW.json';dump(OUT/'ANNOTATIONS.json',ann)
    keys=json.loads((OUT/'KEYFRAME_REVISIONS.json').read_text(encoding='utf-8'));keypairs={(r['subject_id'],r['sar_frame']) for r in keys};dump(OUT/'KEYFRAME_REVISIONS.json',[r for r in rows if (r['subject_id'],r['sar_frame']) in keypairs])
    checks=[]
    def check(name,ok,**details):
        checks.append({'check':name,'passed':bool(ok),**details})
        if not ok:raise RuntimeError(checks[-1])
    old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records'];oldmap={(r['subject_id'],r['sar_frame']):r for r in old}
    check('137 consecutive frames for each of three objects',len(rows)==411 and all(sorted(r['sar_frame'] for r in rows if r['subject_id']==s)==list(range(358,495)) for s in ann['subjects']))
    check('Original selected SAR358 boxes exactly retained',all(r['sar_box']==oldmap[r['subject_id'],358]['sar_box'] for r in rows if r['sar_frame']==358))
    check('No new user confirmations introduced',sum(r['user_confirmed_this_frame'] for r in rows)==3 and all(r['sar_frame']==358 for r in rows if r['user_confirmed_this_frame']))
    manifest=json.loads((OUT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    check('All137 input source hashes preserved',all(sha(r['path'])==r['sha256'] for r in manifest['sar']))
    index=json.loads((ROOT/'output/car_consolidation_20261102/ARTIFACT_INDEX.json').read_text(encoding='utf-8'))
    evidence=[r for r in index if Path(r['path']).is_file() and 'sha256' in r]
    preserved=[{'id':r['id'],'path':r['path'],'unchanged':sha(r['path'])==r['sha256']} for r in evidence]
    check('Previous indexed sources, code and outputs preserved',all(r['unchanged'] for r in preserved),count=len(preserved));dump(OUT/'PRESERVATION.json',preserved)
    corner_sets=[native_corners(*(r['sar_box'][k] for k in ['cx','cy','width','height','rotation_deg'])) for r in rows]
    check('Finite valid boxes inside native image canvas',all(np.isfinite(c).all() and (c[:,0]>=0).all() and (c[:,0]<1024).all() and (c[:,1]>=0).all() and (c[:,1]<592).all() for c in corner_sets))
    check('All137 frames were covered by actual visual review',sorted(f for p in review['pages'] for f in p['frames'])==list(range(358,495)))
    dif=json.loads((OUT/'REVISION_DIFFERENCES.json').read_text(encoding='utf-8'));summary={}
    for s in ann['subjects']:
        end=next(r for r in dif if r['subject']==s and r['frame']==494)
        summary[s]={'last_frame_revision_center_xy_px':end['center_change_xy'],'last_frame_angle_change_deg':end['angle_change_deg'],
                    'max_neighborhood_sensitivity_px':max(r['neighborhood_sensitivity_px'] for r in rows if r['subject_id']==s)}
    dump(OUT/'REVISION_SUMMARY.json',{'role':'VERSION_DIFFERENCE_AND_SENSITIVITY_NOT_ACCURACY','subjects':summary})
    frames=[];opt=data.frames('OPTICAL')
    for f in range(358,495):
        sr=data.frame('SAR',f);o=opt.loc[(opt.optical_timestamp_ms-sr['timestamp_ms_nominal']).abs().idxmin()]
        frames.append({'frame':f,'raw':Path(os.path.relpath(sr['image_path'],OUT)).as_posix(),
                       'optical':Path(os.path.relpath(o.optical_image_path,OUT)).as_posix(),'optical_frame':int(o.optical_frame_index),
                       'delta_ms':float(o.optical_timestamp_ms-sr['timestamp_ms_nominal'])})
    template=(ROOT/'tasks/car_central_static_repair_20261102/review_template.html').read_text(encoding='utf-8')
    (OUT/'index.html').write_text(template.replace('__FRAMES__',json.dumps(frames,ensure_ascii=False)),encoding='utf-8')
    dump(OUT/'DISPLAY_PAIRING.json',{'semantics':'Nearest available optical timestamp to existing SAR358–494; SAR495 not created or clamped; inherited sync uncertainty250ms','frames':frames})
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    videos=[]
    for folder,name in [('sar_frames','CORRECTED_SAR.mp4'),('compare_frames','BEFORE_AFTER.mp4')]:
        p=OUT/name
        if not p.exists():
            subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-n','-framerate','10','-start_number','358','-i',str(OUT/folder/'%06d.jpg'),'-frames:v','137','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(p)],check=True)
        cap=cv2.VideoCapture(str(p));n=0;selected={}
        while True:
            ok,im=cap.read()
            if not ok:break
            if n in [0,62,136]:
                v=OUT/'verification'/f'{p.stem}_{358+n}.jpg';v.parent.mkdir(exist_ok=True);Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)).save(v,quality=95);selected[str(n+358)]=str(v)
            n+=1
        fps=cap.get(cv2.CAP_PROP_FPS);cap.release();check(name+' decoded137 frames',n==137,decoded_frames=n)
        videos.append({'file':name,'frames':n,'playback_fps':10,'source_fps':30,'slowdown':3,'sha256':sha(p),'decoded_inspection_frames':selected})
    dump(OUT/'VERIFICATION.json',{'status':'PASS_TECHNICAL_AND_REVIEW_COVERAGE_NOT_ACCURACY','checks':checks,'videos':videos,'extent_measured_independently':False,'new_user_confirmed_temporal_labels':0})
    text='''# R35三车连续标注修订 v2

2026-11-02。当前修订已生成：002白色SUV、003灰色轿车、005橙色车，SAR358–494，共137帧、411条记录。

[逐帧查看](index.html) · [完整前后对照视频](BEFORE_AFTER.mp4) · [修订版SAR视频](CORRECTED_SAR.mp4) · [末帧对照](keyframes/COMPARE_494.png)

## 实际改了什么

旧版仅根据8个时刻短亮带端点的中点移动原框，方向整段固定。核对真实原图后，改用每帧多结构的局部刚性位移与旋转导航，并实际查看137帧三车原生裁剪图。另以160像素邻域对照100像素主导航，检查位置是否强烈依赖一个局部范围；这不是准确度验证。

末帧相对旧版，002中心修订约(+27.2,-14.0)px，003约(+28.1,-10.2)px，005约(+10.7,-4.3)px。002/003后段旧框偏左的情况在对照中减轻。这些数值是版本差，不能叫真实定位误差或精度提升。

长时单点存活集拟合会在末段产生明显缩小/旋转，已拒绝把它作为车体变形或新车长。新版保持源358长宽，只修订位置和轴向。137帧区域图实际逐帧审阅，16个时相另存关键帧；这些关键帧是导航后复核，不是独立手画真值。

## 尚未完成的部分

远端主体轮廓在SAR中较弱，本次仍继承358原人工框的范围，**没有逐帧独立重测整车长宽**。修订框用虚线表达近似整体参考。它是助手复核后的修订版，仍不作为完整可靠时序GT；没有新增用户确认标注，也没有开始未来预测评测。

## 证据与复现

- [逐帧标注](ANNOTATIONS.json)：原生坐标、位置/方向来源、尺寸来源、用户确认与助手复核分开。
- [关键时相](KEYFRAME_REVISIONS.json)：16时相×3车；SAR358三个人工框逐值保持。
- [实际视觉核查](SEQUENCE_REVIEW.json)：12页覆盖全部137帧，另有完整原图、光学上下文及新旧对照。
- [技术核验](VERIFICATION.json)：连续性、源哈希、旧结果保留、两视频各137帧解码；不代表位置精度认证。
- [源输入](SOURCE_MANIFEST.json)、[原结果保留核验](PRESERVATION.json)、[版本差与敏感性](REVISION_SUMMARY.json)。

视频10帧/秒，源SAR30帧/秒，均为3倍慢放，未丢帧。网页光学按现有SAR时间选最近光学；保留名义同步的不确定性，不把缺失SAR495替换成494。

代码：`tasks/car_central_static_repair_20261102/`。解释器：`python -X utf8 -B`。顺序运行 review.py prepare、track_diagnostic.py（仅导航反例）、pose_navigation.py、build_revision.py；实际完成视觉检查后再运行 deliver.py。旧输出、原人工源文件、PERSON与独立SAR分支未改。
'''
    (OUT/'START_HERE.md').write_text(text,encoding='utf-8')
    shutil.copyfile(report,OUT/'VISUAL_REVIEW.md')
    print(json.dumps({'technical_checks':len(checks),'preserved_indexed_files':len(preserved),'videos':[{k:r[k] for k in ['file','frames','playback_fps']} for r in videos],'output':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
