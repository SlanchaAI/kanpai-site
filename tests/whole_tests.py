"""Offline browser contracts and fail-closed whole-repository inventory."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import trace
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / '.test-output'
# Exact paths: additions of any language must receive a reviewed classification.
INVENTORY = {
    'index.html': 'browser: outcome offer, validation and synthetic submission',
    'arm_risk.html': 'browser: risk offer, validation and synthetic submission',
    'assets/venture-page-v1.css': 'browser: desktop/mobile layout and focus',
    'tests/whole_tests.py': 'executable: unittest, inventory failure paths, traced below',
    'tests/verify_whole_tests.sh': 'executable: real local/CI caller; bash syntax and exit propagation',
    '.github/workflows/tests.yml': 'configuration: CI calls verifier and uploads coverage',
    '.gitignore': 'non-executable: local output exclusions',
    'tests/README.md': 'non-executable: inventory and reproduction documentation',
    'CNAME': 'non-executable: static hosting domain declaration',
}
PAGES = {
    '/index.html': ('arm_outcome', 'Reproduce failed agent runs in minutes', 'Request the replay pilot'),
    '/arm_risk.html': ('arm_risk', 'Stop guessing why agent runs failed', 'See the replay bureau'),
}


def audit(paths):
    missing = sorted(set(paths) - INVENTORY.keys())
    stale = sorted(INVENTORY.keys() - set(paths))
    if missing or stale:
        raise ValueError(f'Unmapped files: {missing}; stale inventory: {stale}')
    return INVENTORY


# Browser-native constraint validation and FormData; never submit to an external service.
BROWSER_TEST = r'''
(async () => {
 const check = (condition, message) => { if (!condition) throw Error(message); };
 try {
  const expected = EXPECTED;
  check(document.querySelector('h1').textContent === expected[1], 'arm headline');
  check(document.querySelector('button').textContent === expected[2], 'arm button');
  check(document.scripts.length === 1, 'unmapped application script');
  check(!Array.from(document.querySelectorAll('*')).some(el => Array.from(el.attributes).some(a => a.name.startsWith('on'))), 'unmapped inline event handler');
  const form = document.querySelector('form');
  check(form.method === 'post' && new URL(form.action).pathname === '/interest', 'form route');
  check(document.querySelector('meta[name="foundry:arm-id"]').content === expected[0], 'arm metadata');
  check(form.elements.arm_id.value === expected[0], 'arm payload');
  for (const [name, meta] of [['contract_digest','contract-digest'], ['experiment_id','experiment-id'], ['venture_id','venture-id']]) {
   check(form.elements[name].value === document.querySelector(`meta[name="foundry:${meta}"]`).content, name);
  }
  let submissions = 0;
  form.addEventListener('submit', e => { e.preventDefault(); submissions++; });
  form.requestSubmit();
  check(submissions === 0 && !form.checkValidity(), 'empty form rejected');
  for (const name of ['work_email','company','role','consent']) {
   const field = form.elements[name];
   check(field.required && document.querySelector(`label[for="${field.id}"]`), 'required labeled '+name);
  }
  form.elements.work_email.value = 'invalid';
  form.elements.company.value = 'Synthetic Co';
  form.elements.role.value = 'Tester';
  form.elements.consent.checked = true;
  form.requestSubmit();
  check(submissions === 0 && form.elements.work_email.validity.typeMismatch, 'invalid email rejected');
  form.elements.work_email.value = 'test@example.invalid';
  for (const name of ['work_email','company','role','consent']) {
   const field = form.elements[name];
   const previous = field.value;
   if (name === 'consent') field.checked = false; else field.value = '';
   form.requestSubmit();
   check(submissions === 0 && field.validity.valueMissing, 'missing '+name+' rejected');
   if (name === 'consent') field.checked = true; else field.value = previous;
  }
  form.requestSubmit();
  check(submissions === 1 && form.checkValidity(), 'valid form accepted');
  const payload = Object.fromEntries(new FormData(form));
  check(payload.work_email === 'test@example.invalid' && payload.company === 'Synthetic Co' && payload.role === 'Tester' && payload.consent === 'yes', 'serialized synthetic payload');
  check(document.styleSheets.length === 1 && document.styleSheets[0].cssRules.length > 20, 'stylesheet loaded');
  const mobile = innerWidth <= 760;
  check(getComputedStyle(document.querySelector('.offer-ledger')).gridTemplateColumns.split(' ').length === (mobile ? 1 : 3), 'responsive ledger');
  check(getComputedStyle(form).gridTemplateColumns.split(' ').length === (mobile ? 1 : 2), 'responsive form');
  check(document.documentElement.scrollWidth <= innerWidth, 'no horizontal overflow');
  form.elements.work_email.focus();
  check(getComputedStyle(form.elements.work_email).outlineStyle === 'solid', 'visible keyboard focus');
  document.body.innerHTML = '<pre id="result">PASS</pre>';
 } catch (error) { document.body.innerHTML = '<pre id="result">FAIL: '+error.message+'</pre>'; }
})();
'''


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in PAGES:
            script = BROWSER_TEST.replace('EXPECTED', json.dumps(PAGES[self.path]))
            content = (ROOT / self.path.lstrip('/')).read_text().replace('</body>', '<script>'+script+'</script></body>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        else:
            super().do_GET()


class WholeTests(unittest.TestCase):
    def test_inventory(self):
        paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
        self.assertEqual(set(audit(paths)), set(paths))
        OUTPUT.mkdir(exist_ok=True)
        (OUTPUT / 'inventory.json').write_text(json.dumps(audit(paths), indent=2))

    def test_inventory_rejects_unmapped_and_stale(self):
        for paths in [list(INVENTORY) + ['forgotten/unimported.rs'], list(INVENTORY)[1:]]:
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                audit(paths)

    def test_browser(self):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        evidence = []
        try:
            for path in PAGES:
                for width in (390, 1280):
                    with self.subTest(page=path, width=width), tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as profile:
                        result = subprocess.run([
                            os.environ['CHROME'], '--headless', '--no-sandbox', '--disable-gpu',
                            '--no-proxy-server', '--disable-background-networking', '--disable-component-update',
                            '--no-first-run', '--no-default-browser-check', '--disable-dev-shm-usage',
                            '--user-data-dir='+profile, '--window-size='+str(width)+',900',
                            '--dump-dom', f'http://127.0.0.1:{server.server_port}{path}',
                        ], capture_output=True, text=True, timeout=60)
                        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                        self.assertIn('<pre id="result">PASS</pre>', result.stdout, result.stdout[-3000:])
                        evidence.append({'page': path, 'width': width, 'result': 'passed'})
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
        (OUTPUT / 'browser-coverage.json').write_text(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    OUTPUT.mkdir(exist_ok=True)
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[os.path.dirname(os.__file__)])
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WholeTests)
    result = tracer.runfunc(unittest.TextTestRunner(verbosity=2).run, suite)
    counts = tracer.results().counts
    coverage = {}
    # Enumerate every Python file before consulting counts: unimported modules get zero.
    for path in sorted(ROOT.rglob('*.py')):
        if '.test-output' in path.parts:
            continue
        lines = trace._find_executable_linenos(str(path))
        hit = sum(counts.get((str(path), line), 0) > 0 for line in lines)
        coverage[str(path.relative_to(ROOT))] = {'executable_lines': len(lines), 'hit_lines': hit}
        if not hit:
            result.addFailure(unittest.FunctionTestCase(lambda: None), (AssertionError, AssertionError('Unexercised module: '+str(path)), None))
    (OUTPUT / 'coverage.json').write_text(json.dumps(coverage, indent=2))
    tracer.results().write_results(show_missing=True, summary=True, coverdir=str(OUTPUT / 'line-coverage'))
    print('Inventory:', json.dumps(INVENTORY, indent=2))
    print('Python coverage (all modules):', json.dumps(coverage))
    print('Browser/static coverage: .test-output/browser-coverage.json; no application scripts exist.')
    raise SystemExit(not result.wasSuccessful())
