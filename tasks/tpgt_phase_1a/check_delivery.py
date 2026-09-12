"""One-off delivery QA: file/clip integrity and actual browser interactions, not a research validation framework."""
from pathlib import Path
import csv,json,hashlib,re,time
import cv2,numpy as np
from playwright.sync_api import sync_playwright
W=Path('D:/profile/research/workspace');O=W/'output/tpgt/phase_1a';A=O/'audit'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvr(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
results=load(A/'pack_build_results.json');Q=csvr(O/'study_queue.csv');U=csvr(O/'provisional_event_universe.csv');byid={r['event_hypothesis_id']:r for r in U}
audit={'kind':'ONE_OFF_DELIVERY_QA_NOT_SCIENTIFIC_VALIDATION','frozen_schema_unchanged':all(sha(p)==h for p,h in load(A/'frozen_0c_before.json').items()),'queue_unchanged_since_pre_sar_selection':sha(O/'study_queue.csv')==load(A/'pre_sar_selection_freeze.json')['queue_sha256'],'event_ids_unique':len(byid)==len(U),'events':len(U),'media':[],'browser':[]}
assert audit['frozen_schema_unchanged'] and audit['queue_unchanged_since_pre_sar_selection'] and audit['event_ids_unique']
sourcecheck={sid:sha(item['path'])==item['sha256'] for sid,item in load(A/'source_manifest.json').items()};assert all(sourcecheck.values());dump(A/'source_hashes_after.json',sourcecheck)
for result in results:
    eid=result['event_id'];p=O/'evidence_packs'/eid;manifest=csvr(p/'frame_manifest.csv');source=load(p/'source_provenance_card.json')
    assert len(manifest)==result['optical_frames']+result['sar_frames']
    for mode in ['optical','sar']:
        rows=[r for r in manifest if r['modality']==mode];frames=[int(r['f']) for r in rows];assert frames==list(range(frames[0],frames[-1]+1));assert all((p/r['path']).is_file() for r in rows)
    for name,n in [('optical_forward.mp4',result['optical_frames']),('optical_reverse.mp4',result['optical_frames']),('sar_pseudocolor.mp4',result['sar_frames']),('sar_gray.mp4',result['sar_frames'])]:
        cap=cv2.VideoCapture(str(p/name));count=0
        while True:
            ok,im=cap.read()
            if not ok:break
            count+=1
        cap.release();assert count==n,(eid,name,count,n);audit['media'].append({'event_id':eid,'clip':name,'all_frames_decoded':count})
    # Lossless SAR stills are compared to original video at beginning/middle/end, and every gray still to its palette-display ancestor.
    rows=[r for r in manifest if r['modality']=='sar'];m=next(x for x in source['source_videos'] if x['modality']=='sar');cap=cv2.VideoCapture(m['source_video'])
    for row in [rows[0],rows[len(rows)//2],rows[-1]]:
        cap.set(cv2.CAP_PROP_POS_FRAMES,int(row['f']));ok,im=cap.read();stored=cv2.imdecode(np.fromfile(p/row['path'],dtype=np.uint8),cv2.IMREAD_COLOR);assert ok and np.array_equal(im,stored),(eid,row['f'])
    cap.release()
    for row in rows:
        color=cv2.imdecode(np.fromfile(p/row['path'],dtype=np.uint8),cv2.IMREAD_COLOR);gray=cv2.imdecode(np.fromfile(p/row['gray'],dtype=np.uint8),cv2.IMREAD_GRAYSCALE);assert np.array_equal(gray,cv2.cvtColor(color,cv2.COLOR_BGR2GRAY))
    assert source['optical_support_ranges']==json.loads(byid[eid]['support_ranges_optical_frames'])
    assert all(x=='' for k,x in load(p/'observation_log_blank.json').items() if k!='event_hypothesis_id')
    print('MEDIA OK',eid,flush=True)
dump(A/'delivery_media_qa.json',audit)
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True,args=['--allow-file-access-from-files'])
    context=browser.new_context(viewport={'width':1500,'height':1050},accept_downloads=True)
    for n,q in enumerate(Q):
        eid=q['event_hypothesis_id'];p=O/'evidence_packs'/eid;page=context.new_page();errors=[];requests=[];page.on('pageerror',lambda er:errors.append(str(er)));page.on('request',lambda r:requests.append(r.url))
        page.goto((p/'OBSERVATION_VIEW.html').as_uri());page.wait_for_function("document.getElementById('sarinfo').textContent.includes('Native SAR')")
        assert not page.locator('#bbox').is_checked();assert all('open_book' not in url.lower() for url in requests)
        first=page.locator('#timeinfo').inner_text();page.locator('#next').click();page.wait_for_function("+document.getElementById('timeline').value===1");page.wait_for_timeout(100);assert page.locator('#timeinfo').inner_text()!=first
        page.locator('#prev').click();page.locator('#optNext').click();page.wait_for_timeout(200);page.locator('#bbox').check();page.locator('#tile').select_option('4');page.wait_for_timeout(200)
        page.locator('#timeline').evaluate("el=>{el.value=Math.floor(+el.max/2);el.dispatchEvent(new Event('input'))}");page.wait_for_timeout(400)
        page.locator('#play').click();page.wait_for_timeout(750);page.locator('#pause').click();page.wait_for_timeout(250);forwardpos=int(page.locator('#timeline').input_value());page.locator('#playBack').click();page.wait_for_timeout(350);page.locator('#pause').click();page.wait_for_timeout(250);assert int(page.locator('#timeline').input_value())<forwardpos
        assert page.evaluate("document.getElementById('sar').width")>500
        page.locator('#offset').fill('100000');page.wait_for_timeout(250);page.locator('#offset').fill('0');page.wait_for_timeout(250)
        page.locator('#bbox').uncheck();page.locator('#timeline').evaluate("el=>{el.value=Math.floor(+el.max/2);el.dispatchEvent(new Event('input'))}");page.wait_for_timeout(350)
        page.screenshot(path=str(A/f'ui_observation_{eid}.png'),full_page=False)
        # All four saved videos can load metadata and decode a frame in the real browser.
        video=[]
        for v in page.locator('video').all():
            v.evaluate("el=>{el.load()}");page.wait_for_function("src=>{let v=[...document.querySelectorAll('video')].find(v=>v.getAttribute('src')===src);return v.readyState>=2}",arg=v.get_attribute('src'),timeout=30000);video.append(v.evaluate("el=>({src:el.getAttribute('src'),duration:el.duration,width:el.videoWidth,height:el.videoHeight})"))
        page.locator('textarea').first.fill('DELIVERY_QA_ONLY')
        with page.expect_download() as dl:page.locator('#saveLog').click()
        dest=A/f'qa_log_export_{eid}.json';dl.value.save_as(dest);assert load(dest)['observations']['what changed']=='DELIVERY_QA_ONLY';page.evaluate('localStorage.clear()');page.locator('textarea').first.fill('');page.evaluate('localStorage.clear()')
        pre=len(requests);page.goto((p/'OPEN_BOOK_VIEW.html').as_uri());page.wait_for_load_state('load');assert 'OPEN_BOOK_VIEW' in page.locator('h1').inner_text();assert not errors,errors
        audit['browser'].append({'event_id':eid,'observation_did_not_request_open_book_resources':True,'frame_step_forward_reverse_crop_offset_and_log_export':'OK','four_video_elements_decoded':video,'page_errors':errors})
        page.close();print('BROWSER OK',eid,flush=True)
    page=context.new_page();page.goto((O/'index.html').as_uri());page.screenshot(path=str(A/'ui_queue.png'),full_page=True);browser.close()
audit['total_native_optical_frames']=sum(x['optical_frames'] for x in results);audit['total_native_sar_frames']=sum(x['sar_frames'] for x in results);audit['display_gray_stills_equal_fixed_conversion']=True;audit['sar_png_samples_equal_source_decode']=True;audit['complete']=True
dump(A/'delivery_qa.json',audit);print(json.dumps({k:v for k,v in audit.items() if k not in ['media','browser']}),flush=True)
