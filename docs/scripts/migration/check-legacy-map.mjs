import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const defaultManifest = join(repoRoot, 'docs/scripts/migration/legacy-routes.json');
const defaultSourceRoot = join(repoRoot, 'docs/content/docs');
const args = process.argv.slice(2);

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function walk(directory, extension) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return walk(path, extension);
    return entry.isFile() && entry.name.endsWith(extension) ? [path] : [];
  });
}

const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const sourceRoot = option('--source-root', defaultSourceRoot);
const manifestPath = option('--manifest', defaultManifest);

try {
  assert.deepEqual(args.filter((arg) => arg.startsWith('--') && !['--manifest', '--source-root'].includes(arg)), ['--source-check']);
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  assert.equal(manifest.routes.length, 38, 'expected 38 authored sources');
  const sources = new Set();
  const urls = new Set();
  const diagrams = [];

  for (const row of manifest.routes) {
    assert.equal(typeof row.source, 'string');
    assert.match(row.source, /^docs\/content\/docs\/(?:[a-z0-9-]+\/)*[a-z0-9-]+\.mdx$/);
    assert.ok(!sources.has(row.source), `duplicate source: ${row.source}`);
    sources.add(row.source);
    assert.equal(typeof row.oldUrl, 'string');
    assert.ok(!urls.has(row.oldUrl), `duplicate old URL: ${row.oldUrl}`);
    urls.add(row.oldUrl);
    const relativeSource = relative('docs/content/docs', row.source).replaceAll(sep, '/');
    const slug = relativeSource.replace(/(?:^|\/)index\.mdx$/, '').replace(/\.mdx$/, '');
    const oldUrl = `/cerbia/docs/${slug ? `${slug}/` : ''}`;
    assert.equal(row.oldUrl, oldUrl, `unexpected old URL: ${row.source}`);
    assert.deepEqual(row.oldUrlVariants, [oldUrl.slice(0, -1), `${oldUrl}index.html`]);
    for (const key of ['targetPageId', 'targetModule', 'nav', 'redirectTarget']) {
      assert.ok(Object.hasOwn(row, key), `missing reserved field: ${key}`);
    }
    const file = join(sourceRoot, relativeSource);
    assert.ok(existsSync(file), `missing source file: ${row.source}`);
    const contents = readFileSync(file);
    assert.equal(row.sha256, sha256(contents), `stale source hash: ${row.source}`);
    const lines = contents.toString('utf8').split('\n');
    assert.equal(row.lineCount, lines.at(-1) === '' ? lines.length - 1 : lines.length, `stale line count: ${row.source}`);
    lines.forEach((line, index) => {
      if (/^\s*```mermaid\s*$/.test(line)) {
        diagrams.push({ source: row.source, line: index + 1, fenceSha256: sha256(line) });
      }
    });
  }

  const actual = walk(sourceRoot, '.mdx').map((path) => `docs/content/docs/${relative(sourceRoot, path).split(sep).join('/')}`);
  assert.deepEqual([...sources].sort(), actual.sort(), 'missing or extra MDX source in frozen inventory');
  assert.equal(diagrams.length, 6, 'expected six Mermaid fences');
  assert.deepEqual(manifest.mermaidFences, diagrams, 'Mermaid fence locations changed');
  assert.equal(manifest.marketingHome.source, 'docs/app/page.tsx');
  assert.equal(manifest.marketingHome.oldUrl, '/cerbia/');
  assert.ok(!urls.has(manifest.marketingHome.oldUrl), 'marketing home must be separate from docs index');
  console.log(`SOURCE_CHECK_OK sources=${sources.size} oldUrls=${urls.size} mermaidFences=${diagrams.length}`);
} catch (error) {
  console.error(`SOURCE_CHECK_FAILED: ${error.message}`);
  process.exitCode = 1;
}
