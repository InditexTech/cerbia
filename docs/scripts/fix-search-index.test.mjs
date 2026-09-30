import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import { createRequire } from 'node:module';

const script = process.env.SEARCH_FIXER ?? join(dirname(fileURLToPath(import.meta.url)), 'fix-search-index.mjs');
const versions = ['prerelease', '0.1.0', '0.1.1'];
const duplicateLatest = createRequire(import.meta.url)('@inditextech/docouture-antora-extensions/lib/duplicate-latest-version.js');

function fixture(context, selectedVersions = versions) {
  const root = mkdtempSync(join(tmpdir(), 'cerbia-search-test-'));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  const site = join(root, 'build/site');
  mkdirSync(join(site, '_/search'), { recursive: true });
  for (const version of selectedVersions) {
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
  return spawnSync(process.execPath, [script, '--site-dir', site], { cwd: dirname(site), encoding: 'utf8' });
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
  assert.match(result.stdout, /files=3/);
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

for (const releases of [[], ['0.1.0'], ['0.1.0', '0.1.1'], ['0.1.0-beta.1+build.2']]) {
  test(`normalizes full history when releases are ${JSON.stringify(releases)}`, (context) => {
    // Given: prerelease plus zero, one, two, or a SemVer-suffixed release.
    const { site } = fixture(context, ['prerelease', ...releases]);
    // When: normalizing all actual indexes.
    const result = run(site);
    // Then: every generated channel succeeds, including prerelease alone.
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, new RegExp(`files=${releases.length + 1} `));
    for (const version of releases) {
      const index = JSON.parse(readFileSync(join(site, '_/search', `ROOT-${version}.json`), 'utf8'));
      assert.equal(index.records[0].url, `/cerbia/${version}/main/about/#section`);
    }
  });
}

for (const version of ['stable', 'latest', 'v0.1.0', '0.1', '01.1.0', '0.1.0-01', '0.1.0+']) {
  test(`rejects unsupported version when index is ${version}`, (context) => {
    // Given: an invalid release or an alias incorrectly presented as an index.
    const { site } = fixture(context, ['prerelease']);
    writeFileSync(join(site, '_/search', `ROOT-${version}.json`), JSON.stringify({ records: [] }));
    // When: running normalization.
    const result = run(site);
    // Then: unsupported versions fail before rewriting.
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /unsupported version:/);
  });
}

test('cooperates with latest files produced by the installed extension', (context) => {
  // Given: the real extension duplicates release HTML, not its shared search asset.
  const { site } = fixture(context);
  const contents = Buffer.from('<dialog data-search-index="ROOT-0.1.1.json"></dialog>');
  const files = [];
  let compose;
  duplicateLatest({ getLogger: () => ({ info() {} }), on: (_event, listener) => { compose = listener; } },
    { duplicateLatestVersion: true });
  compose({ contentCatalog: {
    getComponents: () => [{ name: 'ROOT', latest: { version: '0.1.1', prerelease: false } }],
    getFiles: () => [{ src: { component: 'ROOT', version: '0.1.1' },
      out: { path: '0.1.1/index.html' }, pub: { url: '/0.1.1/' }, contents }],
  }, siteCatalog: { addFile: (file) => files.push(file) } });
  for (const file of files) {
    mkdirSync(dirname(join(site, file.out.path)), { recursive: true });
    writeFileSync(join(site, file.out.path), file.contents);
  }
  // When: fixing indexes with the extension's independent latest copy present.
  const result = run(site);
  // Then: latest keeps the release index reference, whose URLs are canonical.
  assert.equal(result.status, 0, result.stderr);
  assert.equal(readFileSync(join(site, 'latest/index.html'), 'utf8'), contents.toString());
  const index = JSON.parse(readFileSync(join(site, '_/search/ROOT-0.1.1.json'), 'utf8'));
  assert.equal(index.records[0].url, '/cerbia/0.1.1/main/about/#section');
  assert.equal(run(site).stdout.includes('updatedRecords=0'), true);
});

for (const channel of ['stable', 'latest']) {
  test(`rejects orphan channel when ${channel} has no release index`, (context) => {
    // Given: a leftover standalone tree or a latest copy without its index.
    const { site } = fixture(context, ['prerelease']);
    mkdirSync(join(site, channel));
    writeFileSync(join(site, channel, 'index.html'), '<dialog data-search-index="ROOT-0.1.1.json"></dialog>');
    // When: normalizing.
    const result = run(site);
    // Then: the orphan is not silently accepted as a full-history channel.
    assert.notEqual(result.status, 0);
  });
}

for (const url of ['/prerelease/../0.1.0/main/about/', '/prerelease/%2e%2e/main/about/',
  '/cerbia/prerelease/../0.1.0/main/about/', '/prerelease//evil.invalid/main/about/',
  '/cerbia/cerbia/prerelease/main/about/', '/0.1.1/../0.1.0/main/about/', '/latest/main/about/']) {
  test(`rejects unsafe URL when given ${url}`, (context) => {
    // Given: a traversal, ambiguous separator, or repeated mount in an index.
    const { site } = fixture(context);
    const version = url.startsWith('/0.1.1/') ? '0.1.1' : 'prerelease';
    const path = join(site, '_/search', `ROOT-${version}.json`);
    const original = JSON.stringify({ records: [{ url }] });
    writeFileSync(path, original);
    // When: running normalization.
    const result = run(site);
    // Then: the invalid index is rejected without rewriting it.
    assert.notEqual(result.status, 0);
    assert.equal(readFileSync(path, 'utf8'), original);
  });
}

for (const failure of ['missing index', 'symlink index', 'symlink search', 'symlink root', 'symlink version', 'symlink assets', 'symlink latest', 'symlink latest home']) {
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
      case 'symlink latest': symlinkSync(root, join(site, 'latest')); break;
      case 'symlink latest home':
        mkdirSync(join(site, 'latest'));
        symlinkSync(target, join(site, 'latest/index.html')); break;
      default: assert.fail(`unknown fixture: ${failure}`);
    }
    // When: running normalization.
    const result = run(selectedSite);
    // Then: no external file is rewritten.
    assert.notEqual(result.status, 0);
    assert.equal(readFileSync(target, 'utf8'), 'external sentinel');
  });
}
