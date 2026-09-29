#!/usr/bin/env node
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '../../..');

function parse(argv) {
  const options = new Map();
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    assert.ok(['--source', '--site-dir', '--manifest', '--content-root'].includes(key) && !options.has(key), `invalid or duplicate option: ${key}`);
    if (key === '--source') options.set(key, true);
    else {
      const value = argv[++index];
      assert.ok(value && !value.startsWith('--'), `missing value for ${key}`);
      options.set(key, resolve(value));
    }
  }
  assert.ok(!options.has('--source') || !options.has('--site-dir'), 'choose source mode or artifact mode, not both');
  assert.ok(!options.has('--content-root') || !options.has('--site-dir'), '--content-root is source-only');
  return {
    source: !options.has('--site-dir'), site: options.get('--site-dir'),
    manifest: options.get('--manifest') ?? join(here, 'legacy-routes.json'),
    content: options.get('--content-root') ?? join(repo, 'docs/src'),
  };
}

function check(script, args) {
  const result = spawnSync(process.execPath, [join(here, script), ...args], { encoding: 'utf8', timeout: 120000 });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, `${script} failed (${result.status ?? result.signal}): ${result.stderr}${result.stdout}`);
  return result.stdout.trim();
}

try {
  const options = parse(process.argv.slice(2));
  const manifest = JSON.parse(readFileSync(options.manifest, 'utf8'));
  assert.equal(manifest.routes.length, 38, 'expected 38 frozen rows');
  const common = ['--manifest', options.manifest];
  check('check-legacy-map.mjs', ['--source-check', ...common]);
  check('check-legacy-map.mjs', ['--nav', ...common, '--content-root', options.content]);
  check('check-url-contract.mjs', ['--inventory', options.manifest]);
  const contentChecks = [
    ['check-intros.mjs', ['--intros', ...common, '--pages-dir', join(options.content, 'modules/main/pages')]],
    ['check-content-root.mjs', ['--content', '--group', 'root', ...common, '--pages-dir', join(options.content, 'modules/main/pages')]],
    ['check-content-loaders.mjs', ['--content', '--group', 'loaders-preprocessors', ...common, '--pages-dir', join(options.content, 'modules/main/pages')]],
    ['check-content-scanners.mjs', ['--content', '--group', 'scanners-aggregators', ...common, '--content-root', options.content]],
    ['check-content-packages.mjs', ['--content', '--group', 'packages', ...common, '--content-root', options.content]],
  ];
  for (const [script, args] of contentChecks) check(script, args);
  for (const row of manifest.routes) {
    const [module, page] = row.targetPageId.split(':');
    assert.ok(existsSync(join(options.content, 'modules', module, 'pages', `${page}.adoc`)), `missing canonical source page: ${row.targetPageId}`);
  }
  if (options.source) {
    console.log('MIGRATION_SOURCE_OK rows=38 canonicalPages=38 nav=38 packageModules=6 renderedDiagrams=not-checked aliases=not-checked');
  } else {
    check('check-redirects.mjs', ['--site-dir', options.site, ...common]);
    const versions = ['prerelease', ...(existsSync(join(options.site, 'stable/index.html')) ? ['stable'] : [])];
    for (const version of versions) {
      const diagramResult = check('check-diagrams.mjs', [
        '--mode', 'full', '--site-dir', options.site, '--version', version, '--routes', options.manifest,
      ]);
      const diagram = JSON.parse(diagramResult);
      assert.equal(diagram.fullInventoryVerified, true);
      assert.equal(diagram.renderedDiagramCount, 6);
    }
    console.log(`MIGRATION_ARTIFACT_OK rows=38 canonicalPages=38 nav=38 aliases=38 packageModules=6 renderedDiagrams=6-per-version versions=${versions.join(',')}`);
  }
} catch (error) {
  console.error(`MIGRATION_FAILED: ${error.message}`);
  process.exitCode = 1;
}
