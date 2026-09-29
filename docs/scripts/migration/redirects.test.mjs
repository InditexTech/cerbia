import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const manifestPath = join(here, 'legacy-routes.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

function fixture() {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-redirects-test-'));
  const mapped = manifest.routes;
  for (const row of mapped) {
    const [module, page] = row.targetPageId.split(':');
    const source = readFileSync(join(here, '../../src/modules', module, 'pages', `${page}.adoc`), 'utf8');
    assert.match(source, /^= .+/m, `fixture must derive from a real authored page: ${row.targetPageId}`);
  }
  for (const version of ['prerelease', 'stable']) {
    mkdirSync(join(site, version), { recursive: true });
    writeFileSync(join(site, version, 'index.html'), '<main><h1>Real home fixture</h1></main>');
    for (const row of mapped) {
      const [module, page] = row.targetPageId.split(':');
      const target = join(site, version, module, ...(page === 'index' ? [] : page.split('/')), 'index.html');
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, `<nav class="side-menu__nav"><a href="./" aria-current="page">${row.targetPageId}</a></nav><main><h1>${row.targetPageId}</h1><p>Nonempty target fixture.</p></main>`);
    }
  }
  return site;
}

function run(script, site, manifestFile) {
  return spawnSync(process.execPath, [join(here, script), '--site-dir', site, ...(manifestFile ? ['--manifest', manifestFile] : [])], { encoding: 'utf8' });
}

test('Given prerelease targets only, when generating, then 38 aliases resolve to prerelease', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  rmSync(join(site, 'stable'), { recursive: true });
  assert.equal(run('generate-redirects.mjs', site).status, 0);
  assert.equal(run('check-redirects.mjs', site).status, 0);
  assert.match(readFileSync(join(site, 'docs/index.html'), 'utf8'), /href="\/cerbia\/prerelease\/main\/about\/"/);
  assert.equal(run('generate-redirects.mjs', site).status, 1, 'must not overwrite existing aliases');
});

test('Given stable and prerelease targets, when generating, then stable wins', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  assert.equal(run('generate-redirects.mjs', site).status, 0);
  assert.equal(run('check-redirects.mjs', site).status, 0);
  assert.match(readFileSync(join(site, 'docs/packages/cerbia-core/index.html'), 'utf8'), /href="\/cerbia\/stable\/cerbia-core\/"/);
  rmSync(join(site, 'docs/packages/cerbia-core/index.html'));
  assert.equal(run('check-redirects.mjs', site).status, 1, 'removed alias must fail');
});

test('Given missing canonical target, when generating, then no aliases are emitted', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  rmSync(join(site, 'stable/main/about/index.html'));
  assert.equal(run('generate-redirects.mjs', site).status, 1);
  assert.equal(run('check-redirects.mjs', site).status, 1);
});

test('Given malicious route or stale target, when generating, then input is rejected', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  for (const change of [
    (copy) => { copy.routes[0].oldUrl = '/cerbia/docs/../../escape/'; },
    (copy) => { copy.routes[0].targetPageId = 'main:never-created'; copy.routes[0].redirectTarget = 'main:never-created'; },
  ]) {
    const copy = structuredClone(manifest);
    change(copy);
    const file = join(site, 'bad-manifest.json');
    writeFileSync(file, JSON.stringify(copy));
    assert.equal(run('generate-redirects.mjs', site, file).status, 1);
  }
});

test('Given a canonical output collision, when generating, then no existing page is replaced', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const alias = join(site, 'docs/index.html');
  mkdirSync(dirname(alias), { recursive: true });
  writeFileSync(alias, 'canonical page');
  assert.equal(run('generate-redirects.mjs', site).status, 1);
  assert.equal(readFileSync(alias, 'utf8'), 'canonical page');
});

test('Given an unexpected alias or forged redirect, when checking, then artifact fails', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  assert.equal(run('generate-redirects.mjs', site).status, 0);
  const unknown = join(site, 'docs/unknown/index.html');
  mkdirSync(dirname(unknown), { recursive: true });
  writeFileSync(unknown, 'unexpected');
  assert.equal(run('check-redirects.mjs', site).status, 1);
  rmSync(unknown);
  const alias = join(site, 'docs/index.html');
  writeFileSync(alias, readFileSync(alias, 'utf8').replace('/cerbia/stable/main/about/', '/cerbia/stable/main/never-created/'));
  assert.equal(run('check-redirects.mjs', site).status, 1);
});

test('Given an appended executable script, when checking, then artifact fails', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  assert.equal(run('generate-redirects.mjs', site).status, 0);
  const alias = join(site, 'docs/index.html');
  writeFileSync(alias, `${readFileSync(alias, 'utf8')}<script>location.replace("https://example.invalid/")</script>`);
  const result = run('check-redirects.mjs', site);
  assert.equal(result.status, 1, `appended script bypassed checker: ${result.stdout}`);
});

test('Given a symlink in the alias tree, when generating, then path is rejected', (t) => {
  const site = fixture();
  t.after(() => rmSync(site, { recursive: true, force: true }));
  mkdirSync(join(site, 'docs'));
  symlinkSync(site, join(site, 'docs/components'));
  assert.equal(run('generate-redirects.mjs', site).status, 1);
});
