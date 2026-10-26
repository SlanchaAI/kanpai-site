import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { extname } from 'node:path';
import process from 'node:process';
import { HtmlValidate, Parser } from 'html-validate';

// Every file is classified. New languages fail closed until checks are wired.
const metadata = new Set([
  '.git', '.gitignore', 'CNAME', 'package.json', 'package-lock.json',
  '.htmlvalidate.json', '.stylelintrc.json', 'tsconfig.json',
  '.github/workflows/whole-lint.yml',
]);
/** @type {Record<string, string[]>} */
const sources = { '.html': [], '.css': [], '.mjs': [], '.sh': [] };
/** @param {string} directory */
function inventory(directory) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = directory === '.' ? entry.name : `${directory}/${entry.name}`;
    if (path === '.git') {
      process.stdout.write('Excluded .git: Git metadata\n');
    } else if (path === 'node_modules' || path === '.cache') {
      process.stdout.write(`Excluded ${path}/: installed vendor tools or local cache\n`);
    } else if (entry.isDirectory()) {
      inventory(path);
    } else if (metadata.has(path)) {
      process.stdout.write(`Infrastructure: ${path}\n`);
    } else {
      const files = sources[extname(path)];
      if (!files) throw new Error(`Unclassified file: ${path}; add full-scope checks first`);
      files.push(path);
    }
  }
}
inventory('.');
for (const [language, files] of Object.entries(sources)) {
  if (!files.length) throw new Error(`Empty source inventory: ${language}`);
  process.stdout.write(`${language}: ${files.length} files: ${files.join(', ')}\n`);
}
/** @param {string} tool @param {string[]} args */
function run(tool, args) {
  execFileSync(`node_modules/.bin/${tool}`, args, { stdio: 'inherit' });
}
if (process.argv[2] === 'lint') {
  const validator = new HtmlValidate();
  for (const path of sources['.html']) {
    const parser = new Parser(await validator.getConfigFor(path));
    const document = parser.parseHtml(readFileSync(path, 'utf8'));
    for (const element of document.querySelectorAll('*')) {
      if (['script', 'style', 'iframe', 'object', 'embed'].includes(element.tagName)) {
        throw new Error(`${path}: embedded source needs lint/type-check wiring first`);
      }
      for (const attribute of element.attributes) {
        if (attribute.key.startsWith('on') || ['style', 'srcdoc'].includes(attribute.key)) {
          throw new Error(`${path}: embedded source attribute ${attribute.key}`);
        }
      }
    }
  }
  run('html-validate', sources['.html']);
  run('stylelint', sources['.css']);
  run('eslint', ['--no-ignore', '--max-warnings', '0', ...sources['.mjs']]);
  execFileSync(process.env.SHELLCHECK || 'shellcheck', sources['.sh'], { stdio: 'inherit' });
} else if (process.argv[2] === 'typecheck') {
  run('tsc', ['--project', 'tsconfig.json']);
  process.stdout.write('Strict checkJs: all first-party JavaScript. HTML/CSS and shell: no static program types; HTML-validate, Stylelint and ShellCheck cover them.\n');
} else {
  throw new Error('Expected lint or typecheck');
}
