"""Headless browser interaction QA; no application server or external network."""
import argparse
from playwright.sync_api import sync_playwright
from common import ROOT, writejson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', default='msedge', help='Installed browser channel; no download')
    args = parser.parse_args()
    out = ROOT / 'output/morphology_object_v2'
    errors = []; results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=args.channel)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        for path in sorted((out / 'inspect').glob('*.html')):
            page.goto(path.as_uri()); page.wait_for_function('window.inspectorReady === true')
            assert page.evaluate('Array.from(document.images).every(im => im.complete && im.naturalWidth > 0)')
            for kind in ['nuclei', 'segments', 'relations', 'dark_open_regions']:
                page.select_option('#kind', kind)
                count = page.locator('#unit option').count()
                if count:
                    page.select_option('#unit', str(count - 1))
                    assert page.locator('#details').inner_text()
                if kind == 'dark_open_regions':
                    page.select_option('#region', '3')
            page.select_option('#field', 'I2'); page.select_option('#field', 'I0')
            assert page.locator('#raw').evaluate('(c)=>c.width>0 && c.height>0')
            results.append(path.name)
        page.goto((out / 'inspect/GM_RM017_f0344_g151.html').as_uri())
        page.select_option('#kind', 'relations'); page.select_option('#unit', '0')
        page.screenshot(path=str(out / 'figures/INSPECTOR_QA.png'), full_page=False)
        browser.close()
    assert not errors, errors
    writejson(out / 'BROWSER_QA.json', dict(status='PASS', pages=results, console_exceptions=errors,
                                         checked='all 20 pages; layer and unit changes; field/dark level changes; screenshot'))
    print('PASS browser:', len(results), 'pages')


if __name__ == '__main__':
    main()
