"""Browser regression checks for first-open sequence loading and dialog races.

Requires Playwright and Chromium. Use --browser for an existing Chrome binary.
The default test server serves the checked-out static site on loopback only.
"""
import argparse
import asyncio
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.async_api import async_playwright, Error as BrowserError


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


async def check(args, url):
    data = args.site_dir/'data'
    records = json.loads((data/'records.json').read_text(encoding='utf8'))['records']
    first = records[0]
    other = next(r for r in records if r['sha'][:2] != first['sha'][:2])
    # Independent FASTA source, rather than the new derivative JSON files.
    source = {}
    for block in (data/'proteins.faa').read_text(encoding='utf8').split('>')[1:]:
        header, *parts = block.splitlines()
        source[header.split()[0]] = ''.join(parts)
    checks, errors = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, **({'executable_path': str(args.browser)} if args.browser else {}))

        async def fresh():
            context = await browser.new_context()
            page = await context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            bulk = []
            async def block_full(route):
                bulk.append(route.request.url)
                await route.abort()
            await page.route('**/data/proteins.faa', block_full)
            await page.goto(url, wait_until='domcontentloaded')
            await page.locator('#count').filter(has_text='14,505 of 14,505').wait_for()
            return context, page, bulk

        async def loaded(page, row):
            await page.wait_for_function("sequence => document.querySelector('#detail-sequence')?.textContent === sequence", arg=source[row['id']], timeout=5000)
            assert await page.locator('#detail-sequence').get_attribute('aria-busy') == 'false'
            assert await page.locator('#single-fasta').is_enabled()
            assert not await page.locator('#retry-sequence').is_visible()

        # Each entry uses a new browser context, with the full FASTA unavailable.
        for entry in ['.id-link', '.evidence-button']:
            context, page, bulk = await fresh()
            await page.locator('#rows '+entry).first.click()
            await loaded(page, first)
            assert not bulk
            async with page.expect_download() as event:
                await page.locator('#single-fasta').click()
            download = await event.value
            assert Path(await download.path()).read_text() == f'>{first["id"]}\n{source[first["id"]]}\n'
            await context.close()
        checks.append('Cold first-click from both protein and Evidence; exact sequence and single FASTA export; no full FASTA request')
        if not args.public:
            # Release a deliberately slow request without closing the dialog.
            context, page, bulk = await fresh()
            gate, started = asyncio.Event(), asyncio.Event()
            async def slow(route):
                started.set()
                await gate.wait()
                await route.continue_()
            await page.route('**/data/sequences/*.json', slow)
            await page.locator('#rows .id-link').first.click()
            await asyncio.wait_for(started.wait(), 3)
            assert await page.locator('#detail-sequence').get_attribute('aria-busy') == 'true'
            assert await page.locator('#single-fasta').is_disabled()
            gate.set()
            await loaded(page, first)
            assert not bulk
            await context.close()
            checks.append('A slow first request updates the open dialog automatically; download stays disabled until ready')

            # Same-turn close/reopen, then release the old response out of order.
            context, page, bulk = await fresh()
            gate, started, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
            async def out_of_order(route):
                if route.request.url.endswith('/'+first['sha'][:2]+'.json'):
                    started.set()
                    await gate.wait()
                    await route.continue_()
                    finished.set()
                else:
                    await route.continue_()
            await page.route('**/data/sequences/*.json', out_of_order)
            await page.locator('#rows .id-link').first.click()
            await asyncio.wait_for(started.wait(), 3)
            await page.evaluate("id => {document.querySelector('#detail').close(); detail(id);}", other['id'])
            await loaded(page, other)
            gate.set()
            await asyncio.wait_for(finished.wait(), 3)
            await page.wait_for_load_state('networkidle')
            await loaded(page, other)
            await page.locator('#close-detail').click()
            await page.evaluate('id => detail(id)', first['id'])
            await loaded(page, first)
            assert not bulk
            await context.close()
            checks.append('Rapid close/reopen and out-of-order responses keep the selected record correct')

            # Failed requests and invalid responses must be retryable, not cached failures.
            for failure in ['http', 'wrong_sequence', 'null_json', 'timeout']:
                context, page, bulk = await fresh()
                calls = 0
                if failure == 'timeout':
                    await page.evaluate("""() => {
                        const original = window.setTimeout;
                        window.setTimeout = (callback, delay, ...args) => original(callback, delay === 15000 ? 100 : delay, ...args);
                    }""")
                async def fail_once(route):
                    nonlocal calls
                    calls += 1
                    if calls > 1:
                        await route.continue_()
                    elif failure == 'http':
                        await route.fulfill(status=503, body='Temporary failure')
                    elif failure == 'null_json':
                        await route.fulfill(status=200, content_type='application/json', body='null')
                    elif failure == 'wrong_sequence':
                        values = json.loads((data/'sequences'/f'{first["sha"][:2]}.json').read_text())
                        original = values[first['id']]
                        values[first['id']] = ('A' if original[0] != 'A' else 'M')+original[1:]
                        await route.fulfill(status=200, content_type='application/json', body=json.dumps(values))
                    else:
                        await asyncio.sleep(.25)
                        try:
                            await route.continue_()
                        except BrowserError:
                            pass  # The fetch was intentionally aborted by its timeout.
                await page.route('**/data/sequences/*.json', fail_once)
                await page.locator('#rows .evidence-button').first.click()
                await page.locator('#retry-sequence').wait_for(state='visible')
                assert await page.locator('#single-fasta').is_disabled()
                assert await page.locator('#detail-sequence').get_attribute('aria-busy') == 'false'
                await page.locator('#retry-sequence').click()
                await loaded(page, first)
                assert calls == 2 and not bulk
                if failure == 'timeout':
                    await page.wait_for_timeout(300)
                await context.close()
            checks.append('HTTP failure, wrong sequence hash, invalid JSON shape and timeout all recover via Retry')

            # Bulk exports intentionally retain the original complete FASTA path.
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded')
            await page.locator('#count').filter(has_text='14,505 of 14,505').wait_for()
            await page.locator('#search').fill(first['id'])
            async with page.expect_download() as event:
                await page.locator('#export-fasta').click()
            download = await event.value
            assert Path(await download.path()).read_text() == f'>{first["id"]}\n{source[first["id"]]}\n'
            await context.close()
            checks.append('Matched FASTA bulk export is unchanged')
        await browser.close()
    assert not errors, errors
    result = dict(status='PASS', url=url, checks=checks, page_errors=errors)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=Path(__file__).resolve().parents[1]/'website/dist')
    parser.add_argument('--browser', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--public', action='store_true', help='Check cold first opens at the public site; no simulated failures')
    args = parser.parse_args()
    server = None
    if args.public:
        url = 'https://yanshaocheng12.github.io/BacRootFit/'
    else:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(args.site_dir)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/'
    try:
        asyncio.run(check(args, url))
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
