"""Exercise the delivered review page and video with a headless local browser."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/car_central_static_repair_20261102'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='msedge')
    page=browser.new_page(viewport={'width':1300,'height':1000},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((OUT/'index.html').as_uri(),wait_until='load')
    page.wait_for_function('document.querySelector("#sar").complete && document.querySelector("#sar").naturalWidth>0')
    observations=[]
    for frame in [358,420,494]:
        page.locator(f'[data-jump="{frame}"]').click()
        for mode in ['new','compare','raw']:
            page.locator('#mode').select_option(mode)
            page.wait_for_function('document.querySelector("#sar").complete && document.querySelector("#sar").naturalWidth>0')
            observations.append(page.locator('#sar').evaluate('(e)=>({width:e.naturalWidth,height:e.naturalHeight,src:e.getAttribute("src")})'))
    page.locator('#showopt').check()
    page.wait_for_function('document.querySelector("#optical").complete && document.querySelector("#optical").naturalWidth>0')
    optical=page.locator('#optical').evaluate('(e)=>({width:e.naturalWidth,height:e.naturalHeight})')
    page.keyboard.press('ArrowLeft');assert page.locator('#slider').input_value()=='493'
    page.keyboard.press('ArrowRight');assert page.locator('#slider').input_value()=='494'
    page.locator('#play').click();page.wait_for_timeout(350);assert page.locator('#slider').input_value()!='494';page.locator('#play').click()
    page.locator('[data-jump="440"]').click();page.locator('#mode').select_option('compare');page.locator('#showopt').uncheck()
    page.wait_for_function('document.querySelector("#sar").complete && document.querySelector("#sar").naturalWidth===2048')
    page.screenshot(path=str(OUT/'verification/PAGE_DESKTOP.png'),full_page=True)
    page.locator('video').evaluate('(v)=>{v.currentTime=8;return v.play()}')
    page.wait_for_function('document.querySelector("video").readyState>=2 && document.querySelector("video").currentTime>=8')
    video=page.locator('video').evaluate('(v)=>{v.pause();return {width:v.videoWidth,height:v.videoHeight,duration:v.duration,time:v.currentTime}}')
    page.set_viewport_size({'width':420,'height':900});page.screenshot(path=str(OUT/'verification/PAGE_MOBILE.png'),full_page=True)
    assert not errors,errors
    result={'status':'PASS','image_states_checked':len(observations),'observations':observations,'optical_native_size':optical,'video':video,'keyboard_and_playback_checked':True,'console_errors':errors,'meaning':'UI/media behavior only, not annotation truth'}
    (OUT/'verification/PAGE_CHECK.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='observations'},ensure_ascii=False));browser.close()
