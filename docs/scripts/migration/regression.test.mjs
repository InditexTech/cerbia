import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { aliasHtml } from './redirect-routes.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '../../..');
const manifest = JSON.parse(readFileSync(join(here, 'legacy-routes.json'), 'utf8'));

function run(script, ...args) {
  return spawnSync(process.execPath, [join(here, script), ...args], { encoding: 'utf8', timeout: 120000 });
}

function assertFailure(result, reason) {
  assert.equal(result.status, 1, `${reason}: ${result.stdout}${result.stderr}`);
  assert.ok(result.stderr.trim(), `${reason}: no diagnostic`);
}

test('source mode rejects duplicate/unmapped routes, absent nav, and absent canonical source page', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'cerbia-migration-source-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const content = join(root, 'src');
  const file = join(root, 'routes.json');
  cpSync(join(repo, 'docs/src'), content, { recursive: true });
  const args = ['--source', '--manifest', file, '--content-root', content];
  const check = () => run('check-migration.mjs', ...args);
  writeFileSync(file, JSON.stringify(manifest));
  assert.match(run('check-migration.mjs').stdout, /MIGRATION_SOURCE_OK.*renderedDiagrams=not-checked/);
  assert.equal(check().status, 0);
  for (const mutate of [
    (copy) => { copy.routes[1].oldUrl = copy.routes[0].oldUrl; },
    (copy) => { copy.routes[0].targetPageId = 'main:never-created'; copy.routes[0].redirectTarget = 'main:never-created'; },
    (copy) => { copy.routes.push({ ...copy.routes[0], source: 'docs/content/docs/unmapped.mdx' }); },
    (copy) => { copy.routes[0].targetPageId = 'main:../../escape'; copy.routes[0].redirectTarget = 'main:../../escape'; },
  ]) {
    const copy = structuredClone(manifest);
    mutate(copy);
    writeFileSync(file, JSON.stringify(copy));
    assertFailure(check(), 'bad route');
  }
  writeFileSync(file, JSON.stringify(manifest));
  const nav = join(content, 'modules/main/nav.adoc');
  const originalNav = readFileSync(nav, 'utf8');
  writeFileSync(nav, originalNav.replace(/^.*xref:architecture\.adoc\[.*\]\n/m, ''));
  assertFailure(check(), 'missing nav');
  writeFileSync(nav, originalNav);
  rmSync(join(content, 'modules/main/pages/architecture.adoc'));
  assertFailure(check(), 'missing target');
});

test('artifact mode requires every alias, canonical target, and all six rendered diagrams', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-migration-artifact-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const version = 'prerelease';
  mkdirSync(join(site, version), { recursive: true });
  writeFileSync(join(site, version, 'index.html'), '<main><h1>Home</h1></main>');
  const diagrams = new Map();
  for (const fence of manifest.mermaidFences) {
    const id = manifest.routes.find((row) => row.source === fence.source).targetPageId;
    diagrams.set(id, (diagrams.get(id) ?? 0) + 1);
  }
  const image = '<div class="docouture-diagram" data-diagram-type="mermaid"><div><img alt="A meaningful rendered flow diagram" src="data:image/png;base64,YWJj"></div></div>';
  for (const row of manifest.routes) {
    const [module, page] = row.targetPageId.split(':');
    const target = join(site, version, module, ...(page === 'index' ? [] : page.split('/')), 'index.html');
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, `<nav class="side-menu__nav"><a aria-current="page">Current</a></nav><main><h1>${row.targetPageId}</h1>${image.repeat(diagrams.get(row.targetPageId) ?? 0)}</main>`);
  }
  assert.equal(run('generate-redirects.mjs', '--site-dir', site).status, 0);
  const check = () => run('check-migration.mjs', '--site-dir', site);
  assert.equal(check().status, 0);
  const alias = join(site, 'docs/index.html');
  rmSync(alias);
  assertFailure(check(), 'missing alias');
  assert.equal(run('generate-redirects.mjs', '--site-dir', site).status, 1);
  writeFileSync(alias, aliasHtml('/cerbia/prerelease/main/about/'));
  const canonical = join(site, version, 'main/about/index.html');
  rmSync(canonical);
  assertFailure(check(), 'missing canonical target');
  writeFileSync(canonical, `<nav class="side-menu__nav"><a aria-current="page">Current</a></nav><main><h1>About</h1></main>`);
  const diagramPage = join(site, version, 'main/architecture/index.html');
  const originalDiagramPage = readFileSync(diagramPage, 'utf8');
  writeFileSync(diagramPage, readFileSync(diagramPage, 'utf8').replace(image, ''));
  assertFailure(check(), 'missing rendered diagram');
  writeFileSync(diagramPage, originalDiagramPage);
  mkdirSync(join(site, 'stable'), { recursive: true });
  writeFileSync(join(site, 'stable/index.html'), '<main><h1>Stale stable home</h1></main>');
  assertFailure(check(), 'stale partial stable output');
});

test('link checker rejects missing xref, dead docs URL, missing YAML and logo', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'cerbia-migration-links-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const content = join(root, 'src');
  const inbound = join(root, 'README.md');
  cpSync(join(repo, 'docs/src'), content, { recursive: true });
  writeFileSync(inbound, '[Docs](https://inditextech.github.io/cerbia/prerelease/main/about/)\n');
  const args = ['--content-root', content, '--inbound', inbound];
  const check = (...extra) => run('check-links.mjs', ...args, ...extra);
  assert.equal(check().status, 0);
  writeFileSync(inbound, '[Docs](https://inditextech.github.io/cerbia/prerelease/main/not-a-page/)\n');
  assertFailure(check(), 'dead docs URL');
  writeFileSync(inbound, '[Docs](https://inditextech.github.io/cerbia/docs/not-a-page/)\n');
  assertFailure(check(), 'noncanonical docs URL');
  writeFileSync(inbound, '[Docs](https://inditextech.github.io/cerbia/prerelease/main/about/)\n');
  const about = join(content, 'modules/main/pages/about.adoc');
  writeFileSync(about, `${readFileSync(about, 'utf8')}\nxref:missing.adoc[Missing]\n`);
  assertFailure(check(), 'missing xref');
  assertFailure(check('--example-config', join(root, 'missing.yaml')), 'missing YAML');
  assertFailure(check('--logo', join(root, 'missing.png')), 'missing logo');
});
