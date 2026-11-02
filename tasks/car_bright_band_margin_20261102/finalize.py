from pathlib import Path
import hashlib,json,shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'tasks/car_bright_band_margin_20261102'
OUT=ROOT/'output/car_bright_band_margin_20261102'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='msedge')
    page=browser.new_page(viewport={'width':1200,'height':900});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((OUT/'index.html').as_uri(),wait_until='load')
    page.locator('[data-jump="494"]').click()
    page.wait_for_function('document.querySelector("#sar").complete && document.querySelector("#sar").naturalWidth===1024')
    page.locator('#mode').select_option('compare')
    page.wait_for_function('document.querySelector("#sar").complete && document.querySelector("#sar").naturalWidth===2048')
    page.screenshot(path=str(OUT/'verification/PAGE.png'),full_page=True)
    page.locator('video').evaluate('(v)=>{v.currentTime=12;return v.play()}')
    page.wait_for_function('document.querySelector("video").readyState>=2 && document.querySelector("video").currentTime>=12')
    video=page.locator('video').evaluate('(v)=>{v.pause();return {width:v.videoWidth,height:v.videoHeight,duration:v.duration}}')
    assert not errors,errors
    (OUT/'verification/PAGE_CHECK.json').write_text(json.dumps({'status':'PASS','errors':errors,'video':video},indent=2),encoding='utf-8');browser.close()
ann=json.loads((OUT/'ANNOTATIONS.json').read_text(encoding='utf-8'));reviewed=[358,400,420,440,470,494]
for r in ann['records']:
    r['review_state']='MARGIN_VISUALLY_SPOTCHECKED_IN_PREVIEW' if r['sar_frame'] in reviewed else 'MARGIN_RULE_APPLIED_V2_VISUAL_REVIEW_INHERITED'
ann['review_record']='VISUAL_REVIEW.md'
(OUT/'ANNOTATIONS.json').write_text(json.dumps(ann,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'KEYFRAME_REVISIONS.json').write_text(json.dumps([r for r in ann['records'] if r['sar_frame'] in reviewed],ensure_ascii=False,indent=2),encoding='utf-8')
with (TASK/'RUN.md').open('a',encoding='utf-8') as f:f.write('\n完成：6个时相、18个框的预览实际查看；411框单端外放与对端保持检查通过；两视频各137帧；原137源图和344个v2文件哈希保持。新版页面末帧/对照与视频已用系统Edge实际打开。没有再次视觉检查全部137个v3帧。\n')
shutil.copyfile(TASK/'RUN.md',OUT/'RUN.md')
files=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='DELIVERY_MANIFEST.json']
(OUT/'DELIVERY_MANIFEST.json').write_text(json.dumps({'status':'DELIVERED_USER_REQUESTED_MARGIN_V3','files':files,'visual_spotcheck_frames':reviewed,'all137_v3_frames_visually_rechecked':False},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':len(files),'video':video,'annotation_rows':len(ann['records'])}))
