import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from 'node:fs';
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

test('search-index URLs include the mounted base path for prerelease and stable without changing assets', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-migration-search-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const searchDir = join(site, '_/search');
  const cssDir = join(site, '_/css');
  mkdirSync(searchDir, { recursive: true });
  mkdirSync(cssDir, { recursive: true });
  for (const version of ['prerelease', 'stable']) {
    mkdirSync(join(site, version), { recursive: true });
    writeFileSync(join(site, version, 'index.html'), `<main>${version}</main>`);
  }
  const asset = join(cssDir, 'site.css');
  const assetContents = 'body { color: black; }';
  writeFileSync(asset, assetContents);

  for (const version of ['prerelease', 'stable']) {
    writeFileSync(join(searchDir, `ROOT-${version}.json`), JSON.stringify({
      records: [
        { title: 'Keyword scanner', url: `/${version}/main/components/scanners/keyword/` },
        { title: 'Section', url: `/${version}/main/components/scanners/keyword/#parameters` },
        { title: 'Mounted home', url: '/cerbia/' },
        { title: 'Asset', url: '/_/css/site.css' },
        { title: 'External', url: 'https://example.invalid/docs/' },
      ],
    }));
  }

  const normalize = (version) => run('fix-search-index.mjs', '--site-dir', site, '--version', version);
  for (const version of ['prerelease', 'stable']) {
    assert.equal(normalize(version).status, 0);
    const { records } = JSON.parse(readFileSync(join(searchDir, `ROOT-${version}.json`), 'utf8'));
    assert.deepEqual(records.map(({ url }) => url), [
      `/cerbia/${version}/main/components/scanners/keyword/`,
      `/cerbia/${version}/main/components/scanners/keyword/#parameters`,
      '/cerbia/',
      '/_/css/site.css',
      'https://example.invalid/docs/',
    ]);
  }
  assert.equal(normalize('prerelease').status, 0, 'normalizing an already normalized index is idempotent');
  const malformed = join(searchDir, 'ROOT-stable.json');
  for (const url of [
    '/other-version/main/page/',
    '/cerbia/prerelease/main/page/',
    '/cerbia/cerbia/stable/main/page/',
  ]) {
    writeFileSync(malformed, JSON.stringify({ records: [{ url }] }));
    assertFailure(normalize('stable'), `malformed search URL must fail instead of being ignored: ${url}`);
  }
  assert.equal(readFileSync(asset, 'utf8'), assetContents, 'non-search site assets remain unchanged');
  assertFailure(run('fix-search-index.mjs', '--site-dir', join(repo, 'docs/build/site'), '--version', 'stable'),
    'build output is protected unless explicitly selected by a build command');
});

test('search-index fixer rejects URL traversal and noncanonical paths before writing', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-migration-search-url-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  mkdirSync(join(site, 'stable'), { recursive: true });
  mkdirSync(join(site, '_/search'), { recursive: true });
  writeFileSync(join(site, 'stable/index.html'), '<main>stable</main>');
  const path = join(site, '_/search/ROOT-stable.json');
  for (const url of [
    '/stable/../prerelease/main/page/',
    '/stable/%2e%2e/prerelease/main/page/',
    '/cerbia/stable/../prerelease/main/page/',
    '/cerbia/stable/%2e%2e/prerelease/main/page/',
    '/stable//evil.invalid/main/page/',
    '/stable/%6dain/page/',
    '/stable/main/page/%2fadmin/',
    '/stable/main/page/?q=has space',
    '/cerbia/stable/main/page/#bad space',
    '/stable/main/page/?q=%2f',
    '/stable/main/page/#bad%zz',
    '/_/../stable/main/page/',
    '/cerbia/_/../stable/main/page/',
  ]) {
    const original = JSON.stringify({ records: [{ title: 'Unsafe', url }] });
    writeFileSync(path, original);
    const result = run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable');
    assertFailure(result, `unsafe search URL was accepted: ${url}`);
    assert.equal(readFileSync(path, 'utf8'), original, `invalid URL mutated index before rejection: ${url}`);
  }
  const original = JSON.stringify({ records: [{ title: 'Valid', url: '/stable/main/page/?from=search#section' }] });
  writeFileSync(path, original);
  assert.equal(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable').status, 0);
  assert.deepEqual(JSON.parse(readFileSync(path, 'utf8')).records[0].url,
    '/cerbia/stable/main/page/?from=search#section');
  const navigationLinks = {
    query: '/stable/main/page/?query=A%20B&next=%2Fadmin',
    fragment: '/stable/main/page/#part%20one',
    combined: '/stable/main/page/?next=%2Fadmin#part%20one',
  };
  for (const url of Object.values(navigationLinks)) {
    writeFileSync(path, JSON.stringify({ records: [{ url }] }));
    assert.equal(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable').status, 0,
      `well-formed encoded query/fragment should be preserved: ${url}`);
    const rewritten = JSON.parse(readFileSync(path, 'utf8')).records[0].url;
    assert.equal(rewritten, `/cerbia${url}`);
  }
});

test('search-index fixer rejects symlinked site, parent, and index paths without changing external files', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'cerbia-migration-search-symlink-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const site = join(root, 'site');
  const external = join(root, 'external');
  mkdirSync(join(site, 'stable'), { recursive: true });
  mkdirSync(join(site, '_/search'), { recursive: true });
  mkdirSync(join(external, 'stable'), { recursive: true });
  mkdirSync(join(external, '_/search'), { recursive: true });
  writeFileSync(join(site, 'stable/index.html'), '<main>stable</main>');
  writeFileSync(join(external, 'stable/index.html'), '<main>external</main>');
  const externalIndex = join(external, '_/search/ROOT-stable.json');
  const sentinel = JSON.stringify({ records: [{ url: '/stable/main/page/' }] });
  writeFileSync(externalIndex, sentinel);

  const symlinkIndex = join(site, '_/search/ROOT-stable.json');
  symlinkSync(externalIndex, symlinkIndex);
  assertFailure(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable'), 'symlinked search index must be refused');
  assert.equal(readFileSync(externalIndex, 'utf8'), sentinel, 'external index target must remain unchanged');
  rmSync(symlinkIndex);

  const searchDirectory = join(site, '_/search');
  rmSync(searchDirectory, { recursive: true });
  symlinkSync(join(external, '_/search'), searchDirectory, 'dir');
  assertFailure(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable'), 'symlinked search directory must be refused');
  assert.equal(readFileSync(externalIndex, 'utf8'), sentinel, 'external search directory target must remain unchanged');
  unlinkSync(searchDirectory);

  const assetDirectory = join(site, '_');
  rmSync(assetDirectory, { recursive: true });
  symlinkSync(join(external, '_'), assetDirectory, 'dir');
  assertFailure(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable'), 'symlinked asset parent must be refused');
  assert.equal(readFileSync(externalIndex, 'utf8'), sentinel, 'external asset parent target must remain unchanged');
  unlinkSync(assetDirectory);

  const siteAlias = join(root, 'site-alias');
  symlinkSync(site, siteAlias, 'dir');
  assertFailure(run('fix-search-index.mjs', '--site-dir', siteAlias, '--version', 'stable'), 'symlinked site root must be refused');
  assert.equal(readFileSync(externalIndex, 'utf8'), sentinel, 'site-root symlink target must remain unchanged');

  const symlinkedVersion = join(site, 'stable');
  rmSync(symlinkedVersion, { recursive: true });
  symlinkSync(join(external, 'stable'), symlinkedVersion, 'dir');
  assertFailure(run('fix-search-index.mjs', '--site-dir', site, '--version', 'stable'), 'symlinked version directory must be refused');
  assert.equal(readFileSync(externalIndex, 'utf8'), sentinel, 'version-directory symlink target must remain unchanged');
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
