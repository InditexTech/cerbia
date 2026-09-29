#!/usr/bin/env node
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { aliasHtml, basePath, routes, safeFile, selectedVersion } from './redirect-routes.mjs';

const here = dirname(fileURLToPath(import.meta.url));
try {
  const args = process.argv.slice(2);
  assert.ok(args.length === 2 || args.length === 4, 'usage: generate-redirects.mjs --site-dir ISOLATED_ANTORA_OUTPUT [--manifest FILE]');
  assert.equal(args[0], '--site-dir');
  const site = resolve(args[1]);
  const buildDir = resolve(here, '../../build');
  assert.ok(site !== buildDir && !site.startsWith(`${buildDir}/`), 'never stage into docs/build');
  assert.ok(args.length === 2 || args[2] === '--manifest', 'only --manifest may follow --site-dir');
  const mapped = routes(args.length === 4 ? resolve(args[3]) : join(here, 'legacy-routes.json'), join(here, 'url-contract.json'));
  const version = selectedVersion(site, mapped);
  for (const route of mapped) {
    const alias = safeFile(site, route.aliasParts);
    assert.ok(!existsSync(alias), `alias collides with existing output: ${alias}`);
  }
  for (const route of mapped) {
    const alias = safeFile(site, route.aliasParts);
    mkdirSync(dirname(alias), { recursive: true });
    const page = route.targetParts.slice(0, -1).join('/');
    const target = `${basePath}${version}/${page}${page ? '/' : ''}`;
    writeFileSync(alias, aliasHtml(target), { flag: 'wx' });
  }
  console.log(`REDIRECTS_GENERATED aliases=${mapped.length} version=${version} mount=${basePath}`);
} catch (error) {
  console.error(`REDIRECTS_FAILED: ${error.message}`);
  process.exitCode = 1;
}
