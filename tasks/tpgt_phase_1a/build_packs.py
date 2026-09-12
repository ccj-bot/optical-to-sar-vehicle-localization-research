from pathlib import Path
import csv,json,hashlib,math,subprocess,html,time,shutil
from concurrent.futures import ThreadPoolExecutor
import cv2,numpy as np,imageio_ffmpeg
from PIL import Image,ImageDraw
W=Path('D:/profile/research/workspace'); O=W/'output/tpgt/phase_1a'; A=O/'audit'
FF=imageio_ffmpeg.get_ffmpeg_exe()
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvread(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def csvwrite(p,rows,fields=None):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),extrasaction='ignore');w.writeheader();w.writerows(rows)
Q=csvread(O/'study_queue.csv'); D=json.loads((A/'study_source_details.json').read_text(encoding='utf-8')); S=json.loads((A/'source_manifest.json').read_text(encoding='utf-8'))
R={r['run_id']:r for r in csvread(S['C_RUNS']['path'])}
selection={'queue_sha256':sha(O/'study_queue.csv'),'universe_sha256':sha(O/'provisional_event_universe.csv'),'selection_finalized_before_pack_sar_decode':True,'optical_visual_review':'Opening/middle/end optical images inspected. CAR R35 anchor changed to visibly clear large frontal CAR followed by exit; all hypotheses remain in Universe. Anchor is a review role, not completeness certification.','selection_inputs':['optical frames','optical bbox/source observations','run acquisition metadata','source provenance'],'manual_sar_used_for_selection':False}
if (A/'pre_sar_selection_freeze.json').exists():
    old=json.loads((A/'pre_sar_selection_freeze.json').read_text());assert old['queue_sha256']==selection['queue_sha256']
else:dump(A/'pre_sar_selection_freeze.json',selection)
# References are read only after queue materialization. They never enter OBSERVATION_VIEW payloads.
anchorpath=W/'output/person_sar_fullframe_interpolation_review_20260823/repaired_manual_anchor_boxes.csv'
anchors=csvread(anchorpath)
libs=csvread(S['LIBRARY']['path'])
timing=json.loads((W/'output/person_b0_review_closure_timing_semantic_corrections_20260911/ACQUISITION_TIMING_MODEL.json').read_text(encoding='utf-8'))
def saveimg(p,im,quality=94):
    ext=p.suffix;ok,b=cv2.imencode(ext,im,[cv2.IMWRITE_JPEG_QUALITY,quality] if ext=='.jpg' else [cv2.IMWRITE_PNG_COMPRESSION,3]);assert ok;b.tofile(str(p))
def encode(folder,pattern,start,fps,out,reverse=False,scale=None):
    filters=[]
    if scale:filters.append(f'scale={scale}:-2')
    if reverse:filters.append('reverse')
    cmd=[FF,'-hide_banner','-loglevel','error','-y','-framerate',str(fps),'-start_number',str(start),'-i',str(folder/pattern)]
    if filters:cmd+=['-vf',','.join(filters)]
    cmd+=['-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
    return {'path':str(out.relative_to(O)),'command':cmd,'bytes':out.stat().st_size}
def sheet(items,p,title,cols=4):
    width=360;height=234;out=Image.new('RGB',(cols*width,math.ceil(len(items)/cols)*height+34),'#101820');dr=ImageDraw.Draw(out);dr.text((10,9),title,fill='white')
    for i,(path,label) in enumerate(items):
        im=Image.open(path).convert('RGB');im.thumbnail((width,height-28));x=i%cols*width;y=i//cols*height+34;out.paste(im,(x,y+25));dr.text((x+6,y+4),label,fill='white')
    out.save(p,quality=92)
CSS='''body{font:16px/1.55 system-ui,Segoe UI,sans-serif;background:#0d1720;color:#e4edf3;margin:0}main{max-width:1540px;margin:auto;padding:22px}a{color:#85d8e7}h1{font-size:26px}h2{font-size:20px}button,select,input{font:inherit}button,select{padding:6px 12px;background:#244153;color:white;border:1px solid #5c7a8b;border-radius:5px;cursor:pointer}button:hover{background:#365a70}.card{background:#172935;border:1px solid #35505e;border-radius:9px;padding:16px;margin:14px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.triple{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}img,canvas,video{max-width:100%;background:#080c11}canvas{width:100%;cursor:crosshair}label{display:inline-block;margin:5px}textarea{box-sizing:border-box;width:100%;height:70px;background:#0d1720;color:white;padding:8px;border:1px solid #4a6574}pre{white-space:pre-wrap;word-break:break-word;font-size:13px}.tag{color:#ffdb89}.sticky{position:sticky;top:0;background:#142633;padding:12px;z-index:2}.muted{color:#a7bcc8}.wide{width:100%}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #35505e;padding:10px;text-align:left}@media(max-width:850px){.grid,.triple{grid-template-columns:1fr}}'''
def observation_html(data):
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>__TITLE__ · Observation</title><style>__CSS__</style><main>
<a href="../../index.html">← Study Queue</a><h1>OBSERVATION_VIEW · __TITLE__</h1>
<p>先观察真实图像变化，再记录未决解释。这里的 Event 只是有来源支持的时段假设。光学框仅用于指认来源假设；SAR 画面无目标框、评分或人工 reference。</p>
<div class="card tag">灰度 = 伪彩色视频经 cv2.COLOR_BGR2GRAY 的显示派生图，不能解释成原始幅度、RCS 或独立观测。时间轴使用各自 nominal FPS；跨模态对齐仍有不确定性。</div>
<div class="sticky"><button id="prev">← SAR 一帧</button> <button id="playBack">反向</button> <button id="pause">暂停</button> <button id="play">正向</button> <button id="next">SAR 一帧 →</button> <select id="speed"><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1" selected>1×</option></select><br><input id="timeline" type="range" class="wide"><div id="timeinfo"></div></div>
<div class="grid"><div class="card"><h2>光学 · 全画面</h2><label><input id="bbox" type="checkbox">显示来源光学 bbox（不插值）</label><canvas id="opt"></canvas><p><button id="optPrev">← 光学一帧</button> <button id="optNext">光学一帧 →</button> <a id="nativeOpt" target="_blank">打开原分辨率审阅帧</a></p><div id="optinfo"></div></div><div class="card"><h2>SAR · 伪彩色全画面</h2><canvas id="sar"></canvas><div id="sarinfo"></div><a id="nativeSar" target="_blank">打开无损解码 PNG</a></div></div>
<div class="triple"><div class="card"><h2>光学局部与邻域</h2><canvas id="localOpt"></canvas><p class="muted">固定空间窗口：来源光学 bbox 的全时段并集及外围留白。没有跟踪或缺口插值。</p></div><div class="card"><h2>SAR 灰度派生全画面</h2><canvas id="gray"></canvas></div><div class="card"><h2>SAR 局部空间审阅</h2><select id="tile"><option value="0">左上 1/4</option><option value="1">右上 1/4</option><option value="2">左下 1/4</option><option value="3">右下 1/4</option><option value="4">中央 1/4</option></select><canvas id="localSar"></canvas><p class="muted">固定屏幕分区；只是 spatial_control_candidate，未声称空场或可比性。</p></div></div>
<div class="card"><h2>逐流时间偏移审阅</h2><label>SAR 相对光学名义偏移（ms） <input id="offset" type="number" value="0" step="10"></label><p id="timing"></p><p class="muted">滑块走每一张 SAR 帧；光学独立帧按钮可检查所有光学帧。无帧号相等假设。超出本包可用光学时间时明确显示不可用。</p></div>
<details class="card"><summary>Continuous clips · 正放 / 倒放 / 灰度 / 伪彩色</summary><div class="grid"><div><p>Optical forward</p><video controls preload="none" src="optical_forward.mp4"></video></div><div><p>Optical reverse（文件时钟方向相反）</p><video controls preload="none" src="optical_reverse.mp4"></video></div><div><p>SAR pseudocolor</p><video controls preload="none" src="sar_pseudocolor.mp4"></video></div><div><p>SAR derived gray</p><video controls preload="none" src="sar_gray.mp4"></video></div></div></details>
<details class="card"><summary>Contact sheets · 全时段与 before/after</summary><p>Contact sheets 是抽帧导航；上方播放器与帧目录保留整个包的所有解码帧。</p><a href="optical_contact.jpg" target="_blank"><img src="optical_contact.jpg"></a><a href="sar_contact.jpg" target="_blank"><img src="sar_contact.jpg"></a><a href="temporal_context.jpg" target="_blank"><img src="temporal_context.jpg"></a></details>
<details class="card"><summary>Source / provenance card</summary><pre id="sourceCard"></pre></details>
<details class="card"><summary>Uncertainty / UNKNOWN card</summary><pre id="unknownCard"></pre></details>
<details class="card"><summary>Control candidates · 待人工确认</summary><pre id="controls"></pre></details>
<div class="card"><h2>空白 Observation Log</h2><p>记录 what / where / when。不会自动命名 mechanism 或认定 target response。记录保存在当前浏览器，也可导出 JSON。</p><div id="logFields"></div><button id="saveLog">导出观察记录 JSON</button><span id="saved"></span></div>
<div class="card"><p>完成第一遍观察后，可自行打开第二层材料。</p><a href="OPEN_BOOK_VIEW.html">进入 OPEN_BOOK_VIEW →</a></div>
</main><script>const D=__DATA__;
const $=id=>document.getElementById(id);const sl=$('timeline');sl.min=0;sl.max=D.sar.length-1;sl.value=0;let timer=null,si=0,oi=0,lastOpt=null,lastSar=null,paintVersion=0;
function nearest(arr,t){let best=0;for(let i=1;i<arr.length;i++)if(Math.abs(arr[i].t-t)<Math.abs(arr[best].t-t))best=i;return best}
function frameImage(src){return new Promise((ok,fail)=>{const x=new Image();x.onload=()=>ok(x);x.onerror=()=>fail(Error(src));x.src=src})}
function draw(id,im){const c=$(id);c.width=im.naturalWidth;c.height=im.naturalHeight;c.getContext('2d').drawImage(im,0,0)}
function blank(id,text){const c=$(id);c.width=1024;c.height=592;let g=c.getContext('2d');g.fillStyle='#10232f';g.fillRect(0,0,c.width,c.height);g.fillStyle='white';g.font='30px sans-serif';g.fillText(text,40,180)}
function crop(id,im,b){const c=$(id);c.width=Math.max(1,b[2]-b[0]);c.height=Math.max(1,b[3]-b[1]);c.getContext('2d').drawImage(im,b[0],b[1],c.width,c.height,0,0,c.width,c.height)}
function localSar(){if(!lastSar)return;let w=lastSar.naturalWidth,h=lastSar.naturalHeight;let boxes=[[0,0,w/2,h/2],[w/2,0,w,h/2],[0,h/2,w/2,h],[w/2,h/2,w,h],[w/4,h/4,w*3/4,h*3/4]];crop('localSar',lastSar,boxes[+$('tile').value])}
async function render(explicitOpt=false){let version=++paintVersion;si=+sl.value;let sr=D.sar[si],t=sr.t-(+$('offset').value);if(!explicitOpt)oi=nearest(D.optical,t);let op=D.optical[oi];const supported=D.support_ranges.some(([a,b])=>op.f>=a&&op.f<=b);$('timeinfo').textContent=`SAR F${sr.f} · ${sr.t.toFixed(1)} ms | Optical F${op.f} · ${op.t.toFixed(1)} ms | ${supported?'有来源光学观测支持':'BEFORE / AFTER / SUPPORT GAP：未补成 event interval'}`;
let [om,sm,gm]=await Promise.all([frameImage(op.path),frameImage(sr.path),frameImage(sr.gray)]);if(version!==paintVersion)return;lastOpt=om;lastSar=sm;draw('sar',sm);draw('gray',gm);localSar();let available=explicitOpt||(t>=D.optical[0].t-500/D.optical_fps&&t<=D.optical.at(-1).t+500/D.optical_fps);if(available){draw('opt',om);crop('localOpt',om,D.optical_local_bbox);if($('bbox').checked){let ctx=$('opt').getContext('2d');ctx.strokeStyle='#ffda6c';ctx.lineWidth=6;for(const b of (D.boxes[String(op.f)]||[]))ctx.strokeRect(b[0],b[1],b[2]-b[0],b[3]-b[1])}}else{blank('opt','OPTICAL TIME OUTSIDE PACK');blank('localOpt','UNAVAILABLE')}
$('nativeOpt').href=op.path;$('nativeSar').href=sr.path;$('optinfo').textContent=`Native optical F${op.f}; ${supported?'OBSERVED SUPPORT':'context or observation gap'}; source bbox ${(D.boxes[String(op.f)]||[]).length}`;$('sarinfo').textContent=`Native SAR F${sr.f}; no reference overlay`;}
function stop(){clearInterval(timer);timer=null}function step(d){stop();sl.value=Math.max(0,Math.min(D.sar.length-1,+sl.value+d));render()}function play(d){stop();timer=setInterval(()=>{let n=+sl.value+d;if(n<0||n>=D.sar.length){stop();return}sl.value=n;render()},1000/D.sar_fps/(+$('speed').value))}
$('prev').onclick=()=>step(-1);$('next').onclick=()=>step(1);$('pause').onclick=stop;$('play').onclick=()=>play(1);$('playBack').onclick=()=>play(-1);sl.oninput=()=>{stop();render()};$('offset').oninput=()=>render();$('bbox').onchange=()=>render(true);$('tile').onchange=localSar;$('speed').onchange=stop;
function stepOpt(d){stop();oi=Math.max(0,Math.min(D.optical.length-1,oi+d));sl.value=nearest(D.sar,D.optical[oi].t+(+$('offset').value));render(true)}$('optPrev').onclick=()=>stepOpt(-1);$('optNext').onclick=()=>stepOpt(1);
for(const [id,key] of [['sourceCard','source_card'],['unknownCard','unknown_card'],['controls','controls']])$(id).textContent=JSON.stringify(D[key],null,2);$('timing').textContent=D.timing_text;
const fields=['what changed','where','when','relation to local background','relation to other structures','forward/reverse observations','unresolved ambiguity'];const lk='TPGT_PHASE1A_'+D.event_id;let log={};try{log=JSON.parse(localStorage.getItem(lk)||'{}')}catch{};for(const key of fields){const label=document.createElement('label');label.className='wide';label.textContent=key;const ta=document.createElement('textarea');ta.dataset.key=key;ta.value=log[key]||'';ta.oninput=()=>{log[key]=ta.value;try{localStorage.setItem(lk,JSON.stringify(log));$('saved').textContent=' 已保存到当前浏览器'}catch{$('saved').textContent=' 请使用 JSON 导出保存'}};label.appendChild(ta);$('logFields').appendChild(label)}
$('saveLog').onclick=()=>{const b=new Blob([JSON.stringify({event_hypothesis_id:D.event_id,view:'OBSERVATION_VIEW',written_at:new Date().toISOString(),observations:log},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=D.event_id+'_observation_log.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};render();
</script></html>'''
    return template.replace('__TITLE__',html.escape(data['title'])).replace('__CSS__',CSS).replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/'))
def build(q):
    startclock=time.time();eid=q['event_hypothesis_id'];d=D[eid];e=d['event'];rr=d['optical_rows'];run=e['run_id'];r=R[run];p=O/'evidence_packs'/eid;p.mkdir(parents=True,exist_ok=True)
    for name in ['optical_frames','sar_pseudocolor_frames','sar_gray_frames']:(p/name).mkdir(exist_ok=True)
    ofps=float(r['optical_fps']); sfps=float(r['sar_fps']); first=min(a for a,b in e['support_ranges_optical_frames']);last=max(b for a,b in e['support_ranges_optical_frames']);t0=max(0,first/ofps-2);t1=min(float(r['optical_duration_s']), (last+1)/ofps+2)
    ofirst=max(0,math.floor(t0*ofps));olast=min(int(r['optical_frame_count'])-1,math.ceil(t1*ofps)-1);sfirst=max(0,math.floor(t0*sfps));slast=min(int(r['sar_frame_count'])-1,math.ceil(t1*sfps)-1)
    boxes={}
    for row in rr:boxes.setdefault(str(int(row['frame_index'])),[]).append([float(row[k]) for k in ['bbox_x1','bbox_y1','bbox_x2','bbox_y2']])
    bs=np.array([b for values in boxes.values() for b in values]); ow=int(r['optical_width']);oh=int(r['optical_height']);local=[max(0,int(bs[:,0].min())-180),max(0,int(bs[:,1].min())-180),min(ow,int(bs[:,2].max())+180),min(oh,int(bs[:,3].max())+180)]
    media=[];opt=[];sar=[]
    for mode,path,start,end,fps in [('optical',r['optical_video_path'],ofirst,olast,ofps),('sar',r['sar_video_path'],sfirst,slast,sfps)]:
        path=str(Path(path));cap=cv2.VideoCapture(path);assert cap.isOpened(),path;cap.set(cv2.CAP_PROP_POS_FRAMES,start)
        assert abs(cap.get(cv2.CAP_PROP_POS_FRAMES)-start)<0.1
        for f in range(start,end+1):
            ok,im=cap.read();assert ok,(path,f)
            if mode=='optical':
                rel=f'optical_frames/{f:06d}.jpg';saveimg(p/rel,im);opt.append({'f':f,'t':f*1000/fps,'path':rel})
            else:
                rel=f'sar_pseudocolor_frames/{f:06d}.png';gray=f'sar_gray_frames/{f:06d}.png';saveimg(p/rel,im);saveimg(p/gray,cv2.cvtColor(im,cv2.COLOR_BGR2GRAY));sar.append({'f':f,'t':f*1000/fps,'path':rel,'gray':gray})
        cap.release();media.append({'modality':mode,'source_video':path,'sha256':sha(path),'native_fps':fps,'decoded_first_frame':start,'decoded_last_frame':end,'decoded_frames':end-start+1,'native_dimensions':[int(r['optical_width']),int(r['optical_height'])] if mode=='optical' else [int(r['sar_width']),int(r['sar_height'])]})
    commands=[]
    for folder,pat,start,fps,name,rev,scale in [('optical_frames','%06d.jpg',ofirst,ofps,'optical_forward.mp4',False,1920),('optical_frames','%06d.jpg',ofirst,ofps,'optical_reverse.mp4',True,1920),('sar_pseudocolor_frames','%06d.png',sfirst,sfps,'sar_pseudocolor.mp4',False,None),('sar_gray_frames','%06d.png',sfirst,sfps,'sar_gray.mp4',False,None)]:commands.append(encode(p/folder,pat,start,fps,p/name,rev,scale))
    chosenopt=[opt[i] for i in np.linspace(0,len(opt)-1,min(16,len(opt))).astype(int)];chosensar=[sar[i] for i in np.linspace(0,len(sar)-1,min(16,len(sar))).astype(int)]
    sheet([(p/x['path'],f'OPT F{x["f"]} {x["t"]/1000:.3f}s') for x in chosenopt],p/'optical_contact.jpg',f'{run} | optical continuous window, sampled navigation')
    sheet([(p/x['path'],f'SAR F{x["f"]} {x["t"]/1000:.3f}s') for x in chosensar],p/'sar_contact.jpg',f'{run} | pseudocolor; no reference')
    context=[]
    for x in [opt[0],min(opt,key=lambda x:abs(x['f']-first)),min(opt,key=lambda x:abs(x['f']-last)),opt[-1]]:
        context.append((p/x['path'],f'OPT F{x["f"]} '+('BEFORE' if x['f']<first else 'AFTER' if x['f']>last else 'SUPPORT ENDPOINT')))
    for x in [sar[0],min(sar,key=lambda x:abs(x['t']-first*1000/ofps)),min(sar,key=lambda x:abs(x['t']-last*1000/ofps)),sar[-1]]:context.append((p/x['path'],f'SAR F{x["f"]} nominal context'))
    sheet(context,p/'temporal_context.jpg','Presentation before/after only; no event_core/event_context')
    provenance={'event_hypothesis_id':eid,'source_identity':e['source_identity'],'identity_layer':e['identity_layer'],'source_manifest_entry':S[e['source_id']],'source_record_ordinals':e['source_record_ordinals'],'observations':{'source':S[d['observation_source']],'source_record_ordinals':d['observation_ordinals']},'interval_basis':e['interval_basis'],'optical_support_ranges':e['support_ranges_optical_frames'],'source_videos':media,'clip_window_semantics':'Full decoded presentation window, including all unobserved gaps plus up to 2 seconds before/after; not continuous target-support assertion, not event core/context.','optical_storage':'Native-resolution JPEG quality 94 derived directly from source video; videos scaled to width 1920 CRF18. Lossy review exports; native source path and hash retained.','sar_storage':'PNG is lossless relative to decoded pseudocolor source-video pixels. H264 playback clips are lossy copies. Gray uses fixed BGR2GRAY only; palette luminance is not SAR signal intensity.','raw_sar_measurement_ancestor':'UNKNOWN upstream of pseudocolor H264 source','runtime_input_created':False}
    unknown={k:e[k] for k in ['physical_identity_status','canonical_class','distance','pose','completeness','occlusion','truncation','sar_response_presence','sar_localization_validity']};unknown.update({'source_identity_reconciliation':'NOT_PERFORMED; multiple source hypotheses may describe the same measurements','sar_gray':'DISPLAY_LUMINANCE_DERIVED_NOT_ORIGINAL_AMPLITUDE','time_sync':'offset UNKNOWN; nominal per-stream FPS navigation','before_context_clipped_by_acquisition_start':ofirst==0,'after_context_clipped_by_acquisition_end':olast==int(r['optical_frame_count'])-1,'actual_optical_before_context_s':(first-ofirst)/ofps,'actual_optical_after_context_s':(olast-last)/ofps,'event_core_interval':None,'event_context_interval':None,'control_comparability':'UNCONFIRMED','historical_reference_to_this_hypothesis_correspondence':'UNKNOWN'})
    other=[{'event_hypothesis_id':xid,'source_identity':x['event']['source_identity'],'domain':x['event']['domain']} for xid,x in D.items() if xid!=eid and x['event']['run_id']==run and any(not (b<first or a>last) for a,b in x['event']['support_ranges_optical_frames'])]
    controls={'spatial_control_candidate':{'scope':'Fixed SAR quadrants and center window; full frame available','comparability':'UNCONFIRMED'},'temporal_control_candidate':{'optical_before_frames':[ofirst,first-1] if ofirst<first else None,'optical_after_frames':[last+1,olast] if olast>last else None,'comparability':'UNCONFIRMED'},'other_target_control_candidate':{'source_hypotheses':other,'distinct_physical_identity':'UNKNOWN','comparability':'UNCONFIRMED'},'empty_scene_control_candidate':{'scope':'Before/after frames and spatial windows may be inspected for candidate empty areas; no empty-scene evidence established','status':'UNCONFIRMED_NOT_TRUE_NEGATIVE'}}
    timemodel=timing['models'].get(run) if e['domain']=='PERSON' else None
    timetext=(f"{run} PERSON 既有采集审阅包络 [-20,+20] ms；offset=null，非统计置信区间、非精确同步。" if timemodel else f'{run}：使用 native FPS 的名义零偏移导航；实际 offset / drift UNKNOWN，未借用其它域的定时结论。')
    if timemodel:provenance['run_scoped_timing_source']={'path':'output/person_b0_review_closure_timing_semantic_corrections_20260911/ACQUISITION_TIMING_MODEL.json','model':timemodel}
    data={'title':run+' · '+q['domain']+' · '+e['source_identity'],'event_id':eid,'optical_fps':ofps,'sar_fps':sfps,'optical':opt,'sar':sar,'boxes':boxes,'optical_local_bbox':local,'support_ranges':e['support_ranges_optical_frames'],'source_card':provenance,'unknown_card':unknown,'controls':controls,'timing_text':timetext}
    dump(p/'source_provenance_card.json',provenance);dump(p/'uncertainty_unknown_card.json',unknown);dump(p/'control_candidates.json',controls)
    dump(p/'observation_log_blank.json',{'event_hypothesis_id':eid,'what changed':'','where':'','when':'','relation to local background':'','relation to other structures':'','forward/reverse observations':'','unresolved ambiguity':''})
    (p/'OBSERVATION_VIEW.html').write_text(observation_html(data),encoding='utf-8')
    # Whole run/time reference context only. No inferred optical-to-reference identity or interpolation.
    ref=[a for a in anchors if a['run_id']==run and sfirst<=int(a['sar_frame_index'])<=slast]
    lib=[a for a in libs if a['run_id']==run and sfirst<=int(a['sar_frame_index'])<=slast]
    csvwrite(p/'open_book_manual_reference.csv',ref, list(anchors[0]));csvwrite(p/'open_book_historical_library.csv',lib,list(libs[0]))
    manualimgs=[]
    for fi in sorted({int(x['sar_frame_index']) for x in ref}):
        src=p/f'sar_pseudocolor_frames/{fi:06d}.png';im=cv2.imdecode(np.fromfile(src,dtype=np.uint8),cv2.IMREAD_COLOR)
        for a in ref:
            if int(a['sar_frame_index'])!=fi:continue
            rect=((float(a['cx']),float(a['cy'])),(float(a['width']),float(a['height'])),float(a['rotation_deg']));pts=cv2.boxPoints(rect).astype(np.int32);cv2.polylines(im,[pts],True,(40,40,255),2)
        dest=p/f'open_book_reference_F{fi:06d}.png';saveimg(dest,im);manualimgs.append((dest,f'SAR F{fi} historical manual refs'))
    if manualimgs:sheet(manualimgs,p/'open_book_reference_contact.jpg','OPEN BOOK | historical manual reference, no optical identity assignment')
    refdata={'manual_source':{'path':str(anchorpath),'sha256':sha(anchorpath),'scope':'Repaired historical manual anchors; original/repaired IDs retained, no interpolation'},'manual_rows':ref,'historical_library_source':S['LIBRARY'],'historical_library_rows':lib,'correspondence_to_study_event':'UNKNOWN; included by same run and clip time only','used_in_selection':False,'runtime_input':False}
    dump(p/'open_book_reference_card.json',refdata)
    refimage='<img src="open_book_reference_contact.jpg">' if manualimgs else '<p>本片段在已查阅手工 anchor 来源中没有记录。该状态不是 SAR 结构不存在，也不是无 GT 的全域断言。</p>'
    (p/'OPEN_BOOK_VIEW.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>OPEN_BOOK_VIEW</title><style>'+CSS+'</style><main><a href="OBSERVATION_VIEW.html">← OBSERVATION_VIEW</a><h1>OPEN_BOOK_VIEW · '+html.escape(data['title'])+'</h1><div class="card">第二阶段历史材料。所有同 run、同展示时间窗的已有参考均按原语义保留；未将任何框分配给本 Event，未插值。人工 geometry 和历史标签可辅助后续人工探索，但本包不自动生成 mechanism。</div>'+refimage+'<p><a href="open_book_manual_reference.csv">Manual reference CSV</a> · <a href="open_book_historical_library.csv">Historical library CSV</a> · <a href="open_book_reference_card.json">完整来源卡</a></p><pre>'+html.escape(json.dumps(refdata,ensure_ascii=False,indent=2))+'</pre></main></html>',encoding='utf-8')
    csvwrite(p/'frame_manifest.csv',[{'modality':'optical',**x,'gray':''} for x in opt]+[{'modality':'sar',**x} for x in sar],['modality','f','t','path','gray'])
    result={'event_id':eid,'optical_frames':len(opt),'sar_frames':len(sar),'before_after_optical_frames':[ofirst,olast],'support_ranges':e['support_ranges_optical_frames'],'manual_reference_rows_open_book_only':len(ref),'historical_library_rows_open_book_only':len(lib),'clips':commands,'elapsed_s':round(time.time()-startclock,2)};dump(A/f'{eid}_pack_build.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True);return result
if __name__=='__main__':
    results=[]
    # Two independent media builds in parallel; each encoder bounded to two threads.
    with ThreadPoolExecutor(max_workers=2) as ex:
        for res in ex.map(build,Q):results.append(res)
    dump(A/'pack_build_results.json',results)
    index='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TPGT Phase 1A · Study Queue</title><style>'+CSS+'</style><main><h1>TPGT Phase 1A · First Study Queue</h1><p>6 个短事件，CAR / PERSON 各 3 个。逐帧看真实光学与 SAR：先 Observation，再 Open Book。</p><div class="card">Universe 中保留 18,004 条来源层假设，允许弱证据、多版本与 UNKNOWN。它们不是独立物理目标数。Study Queue 只安排研究次序。</div><p><a href="provisional_event_universe.csv">Event Universe CSV</a> · <a href="study_queue.csv">Study Queue CSV</a> · <a href="summary.md">简短 summary</a></p><div class="card tag">灰度视图源自伪彩色显示，非原始幅度；SAR 与光学以各自 FPS 浏览。正式 event_core / event_context 未定义。GT 不进入选择或 runtime input。</div><div class="grid">'
    for q in Q:
        ep='evidence_packs/'+q['event_hypothesis_id']
        index+='<div class="card"><h2>'+q['study_order']+' · '+q['domain']+' · '+q['run_id']+'</h2><p>'+q['source_identity']+' / '+q['study_role']+'</p><a href="'+ep+'/OBSERVATION_VIEW.html"><img src="'+ep+'/optical_contact.jpg"></a><p>'+html.escape(q['selection_basis'])+'</p><a href="'+ep+'/OBSERVATION_VIEW.html">开始 OBSERVATION_VIEW →</a></div>'
    (O/'index.html').write_text(index+'</div></main></html>',encoding='utf-8')
    assert sha(O/'study_queue.csv')==selection['queue_sha256']
