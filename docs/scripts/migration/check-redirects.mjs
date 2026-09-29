#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { aliasHtml, basePath, routes, safeFile, selectedVersion } from './redirect-routes.mjs';

try {
  const args = process.argv.slice(2);
  assert.ok(args.length === 2 || args.length === 4, 'usage: check-redirects.mjs --site-dir ISOLATED_ARTIFACT [--manifest FILE]');
  assert.equal(args[0], '--site-dir');
  assert.ok(args.length === 2 || args[2] === '--manifest', 'only --manifest may follow --site-dir');
  const here = dirname(fileURLToPath(import.meta.url));
  const site = resolve(args[1]);
  const mapped = routes(args.length === 4 ? resolve(args[3]) : join(here, 'legacy-routes.json'), join(here, 'url-contract.json'));
  const version = selectedVersion(site, mapped);
  if (args.length === 2) {
    for (const route of mapped) {
      const [module, page] = route.targetPageId.split(':');
      const nav = join(here, '../../src/modules', module, 'nav.adoc');
      assert.ok(existsSync(nav) && readFileSync(nav, 'utf8').includes(`xref:${page}.adoc[`), `missing source nav entry: ${route.targetPageId}`);
    }
  }
  const expected = new Set();
  for (const route of mapped) {
    const alias = safeFile(site, route.aliasParts);
    assert.ok(existsSync(alias), `missing legacy alias: ${route.oldUrl}`);
    expected.add(alias);
    const page = route.targetParts.slice(0, -1).join('/');
    const target = `${basePath}${version}/${page}${page ? '/' : ''}`;
    assert.equal(readFileSync(alias, 'utf8'), aliasHtml(target), `unexpected alias HTML: ${route.oldUrl}`);
  }
  const docsDir = safeFile(site, ['docs']);
  function visit(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      assert.ok(!entry.isSymbolicLink(), `symlink inside alias tree: ${path}`);
      if (entry.isDirectory()) visit(path);
      else {
        assert.ok(entry.isFile() && expected.has(path), `unknown legacy alias file: ${path}`);
      }
    }
  }
  visit(docsDir);
  assert.equal(expected.size, 38);
  console.log(`REDIRECTS_OK aliases=${expected.size} version=${version} mount=${basePath}`);
} catch (error) {
  console.error(`REDIRECTS_FAILED: ${error.message}`);
  process.exitCode = 1;
}
