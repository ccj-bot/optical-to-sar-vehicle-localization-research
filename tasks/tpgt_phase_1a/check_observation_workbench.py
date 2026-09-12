"""Browser QA for the Phase 1A observation adapter; not scientific validation."""
from pathlib import Path
import json,csv
from playwright.sync_api import sync_playwright
W=Path('D:/profile/research/workspace'); O=W/'output/tpgt/phase_1a'; A=O/'observation_workbench/audit'; A.mkdir(parents=True,exist_ok=True)
Q=list(csv.DictReader((O/'study_queue.csv').open(encoding='utf-8-sig'))); out={'kind':'TPGT_OBSERVATION_WORKBENCH_DELIVERY_QA','events':[]}
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True,args=['--allow-file-access-from-files']); c=b.new_context(viewport={'width':1500,'height':1000},accept_downloads=True)
    for q in Q:
        eid=q['event_hypothesis_id']; page=c.new_page(); req=[]; page.on('request',lambda r:req.append(r.url)); page.goto(f'http://127.0.0.1:8878/evidence_packs/{eid}/OBSERVATION_VIEW.html'); page.wait_for_function("document.querySelector('#sarImage').naturalWidth>0"); page.wait_for_timeout(200)
        assert not any('open_book_registry' in x for x in req), (eid,req)
        assert page.locator('#sarImage').get_attribute('alt')=='SAR'; assert page.locator('#timeline').get_attribute('max')
        box=page.locator('#sarOverlay').bounding_box(); assert box
        page.mouse.move(box['x']+box['width']*.2,box['y']+box['height']*.2); page.mouse.down(); page.mouse.move(box['x']+box['width']*.4,box['y']+box['height']*.45); page.mouse.up(); page.wait_for_timeout(100); assert page.locator('#markList .item').count()==1
        page.locator('#bookmarkType').select_option('CHANGE'); page.locator('#addBookmark').click(); page.locator('#saveObservation').click(); page.wait_for_timeout(250); assert 'r1' in page.locator('#revisionList').inner_text()
        stored=page.evaluate("JSON.parse(localStorage.getItem('TPGT_PHASE1A_OBS_'+window.TPGT_WORKBENCH_DATA.event_hypothesis_id))"); mark=stored['revisions'][0]['spatial_marks'][0]; assert 0<=mark['x1']<mark['x2']<=1024 and 0<=mark['y1']<mark['y2']<=592
        if eid in ('E1A_899fea6cb26d4a25','E1A_3520f2a29d6f636f'):
            with page.expect_download() as dl: page.locator('#contactSheet').click()
            dl.value.save_as(A/f'{eid}_qa_contact_sheet.jpg'); assert (A/f'{eid}_qa_contact_sheet.jpg').stat().st_size>1000
            with page.expect_download() as dl: page.locator('#exportObservation').click()
            exported=A/f'{eid}_qa_revisions.json'; dl.value.save_as(exported); x=json.loads(exported.read_text(encoding='utf-8')); assert x['revisions'][0]==stored['revisions'][0]
        page.reload(); page.wait_for_function("document.querySelector('#sarImage').naturalWidth>0"); assert page.locator('#markList .item').count()==1
        page.locator('#next').click(); page.locator('#playBack').click(); page.wait_for_timeout(250); page.locator('#pause').click(); assert page.locator('#timeinfo').inner_text()
        page.goto(f'http://127.0.0.1:8878/evidence_packs/{eid}/OPEN_BOOK_VIEW.html'); page.wait_for_function("document.querySelector('#sarImage').naturalWidth>0"); page.wait_for_timeout(300); assert any('open_book_registry' in x for x in req)
        if eid=='E1A_3520f2a29d6f636f':
            page.locator('[data-ref="manual_reference"]').check(); page.locator('[data-ref="derived_reference"]').check(); page.wait_for_timeout(100); assert 'MANUAL' in page.locator('#referenceLegend').inner_text() and 'DERIVED' in page.locator('#referenceLegend').inner_text()
        page.locator('#observationText').fill('post open book note'); page.locator('#saveObservation').click(); page.wait_for_timeout(150); assert 'r2' in page.locator('#revisionList').inner_text(); final=page.evaluate("JSON.parse(localStorage.getItem('TPGT_PHASE1A_OBS_'+window.TPGT_WORKBENCH_DATA.event_hypothesis_id))"); assert final['revisions'][0]['observation_id']==final['revisions'][1]['observation_id'] and final['revisions'][0]['observation_phase']=='PRE_OPEN_BOOK' and final['revisions'][1]['observation_phase']=='POST_OPEN_BOOK'
        out['events'].append({'event_hypothesis_id':eid,'blind_no_open_book_request':True,'native_images_loaded':True,'roi_round_trip_reload':'OK','serialization_export_reload':'OK','bookmark_and_revision':'OK','contact_sheet':'OK' if eid in ('E1A_899fea6cb26d4a25','E1A_3520f2a29d6f636f') else 'covered_by_two_clean_anchors','open_book_registry_loaded_only_after_navigation':True,'forward_reverse_step':'OK'}); page.close()
    b.close()
out['complete']=True
(A/'observation_workbench_qa.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(out,ensure_ascii=False))
