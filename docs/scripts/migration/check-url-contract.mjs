import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = dirname(fileURLToPath(import.meta.url));
const defaultContract = join(directory, 'url-contract.json');
const defaultInventory = join(directory, 'legacy-routes.json');
const frozenRouteHash = '0485e23cc02248b3eba0ee8942b06806bbb8c457a58b2efedfa95992d7ab265f';
const args = process.argv.slice(2);

function pathOption(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function checkPath(url, output, basePath) {
  assert.equal(typeof url, 'string', 'invalid URL type');
  assert.ok(!url.includes('/ROOT/') && !url.includes('/cerbia/cerbia/'), `doubled component/cerbia segment: ${url}`);
  assert.ok(!/\/v\d+(?:\.|\/)/.test(url), `code tag used as docs version: ${url}`);
  assert.match(url, /^\/[a-z0-9/-]+\/$/, `invalid URL: ${url}`);
  assert.ok(url.startsWith(basePath), `URL outside site base: ${url}`);
  assert.equal(output, `${url.slice(basePath.length)}index.html`, `wrong artifact output for ${url}`);
  assert.ok(!output.includes('..') && !output.startsWith('/'), `unsafe output: ${output}`);
}

function mappedRoute(inventory, source, oldUrl) {
  const rows = inventory.routes.filter((row) => row.source === source);
  assert.equal(rows.length, 1, `expected one mapped source: ${source}`);
  const row = rows[0];
  assert.equal(row.oldUrl, oldUrl, `wrong old URL for ${source}`);
  assert.equal(row.redirectTarget, row.targetPageId, `stale redirect for ${source}`);
  assert.match(row.targetPageId, /^[a-z0-9-]+:[a-z0-9/-]+$/, `invalid mapped page ID: ${source}`);
  assert.equal(row.targetPageId.split(':')[0], row.targetModule, `mapped module mismatch: ${source}`);
  return row.targetPageId;
}

function pagePath(pageId, version, basePath) {
  const [module, resource] = pageId.split(':');
  const page = resource === 'index' ? '' : `${resource}/`;
  return `${basePath}${version}/${module === 'ROOT' ? '' : `${module}/`}${page}`;
}

try {
  assert.ok(args.every((arg, index) => (index % 2 === 0 ? ['--contract', '--inventory'].includes(arg) : !arg.startsWith('--'))), 'usage: check-url-contract.mjs [--contract FILE] [--inventory FILE]');
  assert.equal(new Set(args.filter((arg) => arg.startsWith('--'))).size, args.length / 2, 'duplicate option');
  const contract = JSON.parse(readFileSync(pathOption('--contract', defaultContract), 'utf8'));
  const inventory = JSON.parse(readFileSync(pathOption('--inventory', defaultInventory), 'utf8'));
  assert.equal(contract.schemaVersion, 1);
  assert.equal(contract.origin, 'https://inditextech.github.io');
  assert.equal(contract.siteUrl, 'https://inditextech.github.io/cerbia');
  assert.equal(contract.basePath, '/cerbia/');
  assert.equal(contract.artifactRoot, 'docs/build/site');
  assert.equal(contract.artifactMount, contract.basePath);
  assert.equal(contract.component, 'ROOT', 'component must be ROOT');
  assert.equal(contract.startPage, 'ROOT::index.adoc');
  assert.equal(contract.marketingPage, 'ROOT:index.adoc');
  assert.equal(contract.urlStyle, 'indexify');

  const docsIndexId = mappedRoute(inventory, 'docs/content/docs/index.mdx', '/cerbia/docs/');
  const keywordId = mappedRoute(inventory, 'docs/content/docs/components/scanners/keyword.mdx', '/cerbia/docs/components/scanners/keyword/');
  const packageId = mappedRoute(inventory, 'docs/content/docs/packages/cerbia-core.mdx', '/cerbia/docs/packages/cerbia-core/');
  assert.equal(inventory.marketingHome.targetPageId, 'ROOT:index', 'marketing home must map to ROOT:index');
  assert.notEqual(docsIndexId, inventory.marketingHome.targetPageId, 'docs index must differ from marketing home');
  assert.equal(contract.docsIndexPage, docsIndexId, 'docs index must match mapped target');

  const versions = contract.versioning;
  assert.equal(versions.mode, 'standalone');
  assert.equal(versions.branchSelector, 'main');
  assert.equal(versions.tagSelector, 'docs/stable');
  assert.deepEqual(versions.prereleaseDescriptor, { version: 'prerelease', prerelease: true });
  assert.equal(versions.stableDescriptor.version, 'stable', 'code tag cannot be a docs version');
  assert.equal(versions.stableDescriptor.prerelease, false);
  assert.deepEqual(versions.absentStable, { versions: ['prerelease'], legacyTargetVersion: 'prerelease' });
  assert.deepEqual(versions.presentStable, { versions: ['prerelease', 'stable'], legacyTargetVersion: 'stable' });
  assert.equal(versions.codeTagPattern, 'v*');
  assert.equal(versions.codeTagDocsVersion, false, 'code tag cannot be a docs version');
  assert.equal(versions.latestVersionSegment, null, 'no latest-version replacement of stable paths');

  const expectedPaths = {
    marketingRoot: ['/cerbia/', 'index.html'],
    prereleaseMarketing: ['/cerbia/prerelease/', 'prerelease/index.html'],
    stableMarketing: ['/cerbia/stable/', 'stable/index.html'],
    prereleaseDocsIndex: ['/cerbia/prerelease/main/about/', 'prerelease/main/about/index.html'],
    stableDocsIndex: ['/cerbia/stable/main/about/', 'stable/main/about/index.html'],
    prereleaseComponentTopic: ['/cerbia/prerelease/main/components/scanners/keyword/', 'prerelease/main/components/scanners/keyword/index.html'],
    stableComponentTopic: ['/cerbia/stable/main/components/scanners/keyword/', 'stable/main/components/scanners/keyword/index.html'],
    prereleasePackageTopic: ['/cerbia/prerelease/cerbia-core/', 'prerelease/cerbia-core/index.html'],
    stablePackageTopic: ['/cerbia/stable/cerbia-core/', 'stable/cerbia-core/index.html'],
    oldDocsIndexAlias: ['/cerbia/docs/', 'docs/index.html'],
  };
  assert.deepEqual(Object.keys(contract.paths).sort(), Object.keys(expectedPaths).sort());
  for (const [key, [url, output]] of Object.entries(expectedPaths)) {
    checkPath(contract.paths[key].url, contract.paths[key].output, contract.basePath);
    assert.equal(contract.paths[key].url, url, `${key} URL`);
    assert.equal(contract.paths[key].output, output, `${key} output`);
  }
  assert.equal(contract.paths.marketingRoot.role, 'site start-page entry to the ROOT marketing home');
  for (const [stem, mappedId] of [['DocsIndex', docsIndexId], ['ComponentTopic', keywordId], ['PackageTopic', packageId]]) {
    for (const version of ['prerelease', 'stable']) {
      const path = contract.paths[`${version}${stem}`];
      assert.equal(path.pageId, mappedId, `${version}${stem} must match mapped target`);
      assert.equal(path.url, pagePath(mappedId, version, contract.basePath), `${version}${stem} must resolve mapped page ID`);
    }
  }
  assert.equal(contract.paths.oldDocsIndexAlias.pageId, docsIndexId, 'old docs index alias must target mapped docs page');
  assert.notEqual(contract.paths.oldDocsIndexAlias.url, contract.paths.marketingRoot.url, 'docs index alias must differ from marketing root');

  assert.equal(inventory.marketingHome.oldUrl, contract.paths.marketingRoot.url);
  const oldUrls = inventory.routes.map((route) => route.oldUrl);
  assert.equal(oldUrls.length, 38, 'expected 38 frozen old routes');
  assert.equal(new Set(oldUrls).size, 38, 'duplicate inventory URL');
  assert.equal(createHash('sha256').update([...oldUrls].sort().join('\n')).digest('hex'), frozenRouteHash, 'frozen task-1 route inventory changed');
  assert.equal(contract.legacyAliases.length, 38, 'expected exactly 38 aliases');
  assert.equal(new Set(contract.legacyAliases).size, 38, 'duplicate alias');
  assert.deepEqual([...contract.legacyAliases].sort(), [...oldUrls].sort(), 'missing or unexpected old URL alias');
  assert.equal(contract.paths.oldDocsIndexAlias.url, '/cerbia/docs/');
  assert.equal(oldUrls.filter((url) => url === '/cerbia/docs/').length, 1);
  for (const alias of contract.legacyAliases) {
    checkPath(alias, `${alias.slice(contract.basePath.length)}index.html`, contract.basePath);
    assert.ok(alias.startsWith('/cerbia/docs/'), `alias outside old docs namespace: ${alias}`);
  }
  assert.deepEqual(contract.legacyPolicy.variants, ['trailing-slash', 'slashless', 'index.html']);
  assert.match(contract.legacyPolicy.entry, /static index\.html/);
  assert.match(contract.legacyPolicy.slashlessCaveat, /Pages-equivalent/);
  assert.match(contract.legacyPolicy.target, /redirectTarget/);
  assert.match(contract.legacyPolicy.target, /404/);
  assert.match(contract.legacyPolicy.withJavaScript, /location\.search and location\.hash unchanged/);
  assert.match(contract.legacyPolicy.withoutJavaScript, /visible link and noscript link/);
  assert.deepEqual(contract.publication.events, ['push:main with docs-relevant paths', 'push:docs/stable', 'optional push:v* republish only']);
  assert.match(contract.publication.release, /separate intentional docs release/);
  assert.match(contract.publication.codeTagAction, /fetch actual main and docs\/stable refs/);
  assert.match(contract.publication.noStableFallback, /prerelease only/);
  assert.equal(contract.publication.pagesConcurrencyGroup, 'cerbia-docs-pages');
  assert.equal(contract.publication.cancelInProgress, false);
  assert.equal(contract.publication.uploadAction, 'actions/upload-pages-artifact');
  assert.equal(contract.publication.deployAction, 'actions/deploy-pages');
  assert.match(contract.fixtureBuildConfirmation, /task 4 isolated HEAD build confirmed/);
  assert.match(contract.fixtureBuildConfirmation, /Stable paths remain intended pending a local stable-ref build in task 16/);

  console.log('URL_CONTRACT_OK aliases=38 deep=37 component=ROOT absent=prerelease present=stable');
} catch (error) {
  console.error(`URL_CONTRACT_FAILED: ${error.message}`);
  process.exitCode = 1;
}
