"""Full inventory and offline execution checks for this dependency-free site."""
from functools import partial
from hashlib import sha256
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Any new file needs explicit review, including hidden CI/build manifests.
FILES = {
    'CNAME', 'index.html', 'arm_risk.html', 'assets/venture-page-v1.css',
    'tests/verify_whole_deps.sh', 'tests/test_whole_deps.py',
    '.github/workflows/whole-deps.yml', 'DEPENDENCY_AUDIT.md',
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class WholeDependencies(unittest.TestCase):
    def test_full_inventory(self):
        files = set()
        for path in ROOT.rglob('*'):
            if '.git' in path.relative_to(ROOT).parts:
                continue
            self.assertFalse(path.is_symlink(), f'Unreviewed symlink: {path}')
            if path.is_file():
                files.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(files, FILES, 'Inventory changed: review dependencies and audit every new ecosystem')
        print('\nInventory:', ', '.join(sorted(files)))
        print('Package manifests/lockfiles/workspaces: 0; production/dev dependencies: 0')
        print('npm/pip/cargo/Go audits: N/A (no corresponding ecosystems)')
        print('Outdated packages/advisories/version holds: none applicable; no suppressions')

    def test_pages_and_local_resources(self):
        for name in ('index.html', 'arm_risk.html'):
            with self.subTest(page=name):
                page = Page()
                page.feed((ROOT / name).read_text())
                self.assertTrue(any(tag == 'html' for tag, _ in page.tags))
                styles = []
                forms = []
                for tag, attrs in page.tags:
                    self.assertNotIn(tag, ('script', 'iframe', 'object', 'embed', 'style'))
                    self.assertFalse(any(key.startswith('on') or key == 'style' for key in attrs))
                    for key in ('src', 'srcset', 'poster', 'data'):
                        self.assertNotIn(key, attrs, f'Unreviewed asset in {name}')
                    if 'href' in attrs:
                        self.assertIn((tag, attrs.get('rel'), attrs['href']), (
                            ('link', 'icon', 'data:,'),
                            ('link', 'stylesheet', '/assets/venture-page-v1.css'),
                        ))
                    if tag == 'link' and attrs.get('rel') == 'stylesheet':
                        styles.append(attrs['href'])
                    if tag == 'form':
                        forms.append((attrs.get('action'), attrs.get('method')))
                self.assertEqual(styles, ['/assets/venture-page-v1.css'])
                self.assertEqual(forms, [('/interest', 'post')])
        # Byte fingerprint of reviewed first-party CSS: no imports, URLs,
        # bundled libraries or web fonts. Changes require a fresh source review.
        self.assertEqual(sha256((ROOT / 'assets/venture-page-v1.css').read_bytes()).hexdigest(),
                         '377e97102cdfac011f989fd94566028c574bf1bf91f0c19aad3e98074722abee')

    def test_http_serving(self):
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route, file in (('/', 'index.html'), ('/arm_risk.html', 'arm_risk.html'),
                                ('/assets/venture-page-v1.css', 'assets/venture-page-v1.css')):
                with urlopen(f'http://127.0.0.1:{server.server_port}{route}', timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), (ROOT / file).read_bytes())
            print('Coverage: both HTML arms and stylesheet served over loopback; no form submission')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
