"""Optional local-file browser QA; no proposal execution or network downloads."""
import re
from urllib.parse import unquote, urlsplit
from playwright.sync_api import sync_playwright
from run_probe import OUT, write


def main():
    report = (OUT / 'REPORT.md').read_text(encoding='utf8')
    report_images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', report)
    for link in report_images:
        assert (OUT / link).is_file(), link
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1500, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((OUT / 'INDEX.html').as_uri(), wait_until='load')
        page.locator('details').evaluate_all('(items) => items.forEach(e => e.open = true)')
        page.wait_for_function('Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)')
        links = page.locator('a').evaluate_all('(items) => items.map(e => e.getAttribute("href"))')
        for link in links:
            parsed = urlsplit(link)
            assert not parsed.scheme and not parsed.netloc, link
            assert (OUT / unquote(parsed.path)).is_file(), link
        image_count = page.locator('img').count()
        page.screenshot(path=str(OUT / 'figures/REVIEW_BROWSER_QA.png'))
        browser.close()
    assert not errors, errors
    result = dict(status='PASS_LOCAL_REVIEW_LINKS_AND_IMAGE_LOADING',
                  browser='installed Edge, headless, local files only',
                  images_loaded=image_count, local_links=len(links),
                  report_image_links=len(report_images), page_errors=errors,
                  scope='presentation QA, not scientific validation')
    write(OUT / 'REVIEW_QA.json', result)
    print(result)


if __name__ == '__main__':
    main()
