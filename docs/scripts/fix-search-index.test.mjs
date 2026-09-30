import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const script = process.env.SEARCH_FIXER ?? join(dirname(fileURLToPath(import.meta.url)), 'fix-search-index.mjs');
const versions = ['prerelease', 'stable'];

function fixture(context) {
  const root = mkdtempSync(join(tmpdir(), 'cerbia-search-test-'));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  const site = join(root, 'build/site');
  mkdirSync(join(site, '_/search'), { recursive: true });
  for (const version of versions) {
    mkdirSync(join(site, version));
    writeFileSync(join(site, version, 'index.html'), '<html>home</html>');
    writeFileSync(join(site, '_/search', `ROOT-${version}.json`), JSON.stringify({ records: [
      { url: `/${version}/main/about/#section` },
      { url: `/cerbia/${version}/main/about/` },
    ] }));
  }
  return { root, site };
}

function run(site) {
  return spawnSync(process.execPath, [script, '--site-dir', site], { encoding: 'utf8' });
}

test('normalizes every generated version when invoked once without git refs', (context) => {
  // Given: actual generated index names and distinct version URLs.
  const { site } = fixture(context);
  // When: running the fixer once.
  const result = run(site);
  // Then: each index has exactly one mount prefix.
  assert.equal(result.status, 0, result.stderr);
  for (const version of versions) {
    const index = JSON.parse(readFileSync(join(site, '_/search', `ROOT-${version}.json`), 'utf8'));
    assert.deepEqual(index.records.map((record) => record.url), [
      `/cerbia/${version}/main/about/#section`, `/cerbia/${version}/main/about/`,
    ]);
  }
});

test('uses build/site when no site option is supplied', (context) => {
  // Given: the conventional generated output in an isolated working directory.
  const { root } = fixture(context);
  // When: running the default CLI.
  const result = spawnSync(process.execPath, [script], { cwd: root, encoding: 'utf8' });
  // Then: every generated index is processed.
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /files=2/);
});

test('preserves normalized bytes when invoked again', (context) => {
  // Given: indexes already normalized by a successful first invocation.
  const { site } = fixture(context);
  assert.equal(run(site).status, 0);
  const path = join(site, '_/search/ROOT-prerelease.json');
  const original = readFileSync(path, 'utf8');
  // When: running the fixer again.
  const result = run(site);
  // Then: the operation is idempotent.
  assert.equal(result.status, 0, result.stderr);
  assert.equal(readFileSync(path, 'utf8'), original);
  assert.match(result.stdout, /updatedRecords=0/);
});

test('rejects generated indexes outside prerelease and stable', (context) => {
  // Given: an output containing a SemVer index instead of a standalone channel.
  const { site } = fixture(context);
  writeFileSync(join(site, '_/search/ROOT-1.0.0.json'), JSON.stringify({ records: [] }));
  // When: running normalization.
  const result = run(site);
  // Then: the unsupported index is rejected before any rewrite.
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unsupported version: 1\.0\.0/);
});

for (const url of ['/prerelease/../0.1.0/main/about/', '/prerelease/%2e%2e/main/about/',
  '/cerbia/prerelease/../0.1.0/main/about/', '/prerelease//evil.invalid/main/about/',
  '/cerbia/cerbia/prerelease/main/about/']) {
  test(`rejects unsafe URL when given ${url}`, (context) => {
    // Given: a traversal, ambiguous separator, or repeated mount in an index.
    const { site } = fixture(context);
    const path = join(site, '_/search/ROOT-prerelease.json');
    const original = JSON.stringify({ records: [{ url }] });
    writeFileSync(path, original);
    // When: running normalization.
    const result = run(site);
    // Then: the invalid index is rejected without rewriting it.
    assert.notEqual(result.status, 0);
    assert.equal(readFileSync(path, 'utf8'), original);
  });
}

for (const failure of ['missing index', 'symlink index', 'symlink search', 'symlink root', 'symlink version', 'symlink assets']) {
  test(`fails safely when the generated output has a ${failure}`, (context) => {
    // Given: an incomplete output or symlink into another location.
    const { root, site } = fixture(context);
    const path = join(site, '_/search/ROOT-prerelease.json');
    const target = join(root, 'external.json');
    writeFileSync(target, 'external sentinel');
    let selectedSite = site;
    switch (failure) {
      case 'missing index': rmSync(path); break;
      case 'symlink index': rmSync(path); symlinkSync(target, path); break;
      case 'symlink search':
        rmSync(join(site, '_/search'), { recursive: true });
        symlinkSync(root, join(site, '_/search')); break;
      case 'symlink root': selectedSite = join(root, 'linked'); symlinkSync(site, selectedSite); break;
      case 'symlink version':
        rmSync(join(site, 'prerelease'), { recursive: true });
        symlinkSync(root, join(site, 'prerelease')); break;
      case 'symlink assets':
        rmSync(join(site, '_'), { recursive: true });
        symlinkSync(root, join(site, '_')); break;
      default: assert.fail(`unknown fixture: ${failure}`);
    }
    // When: running normalization.
    const result = run(selectedSite);
    // Then: no external file is rewritten.
    assert.notEqual(result.status, 0);
    assert.equal(readFileSync(target, 'utf8'), 'external sentinel');
  });
}
