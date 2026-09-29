import assert from 'node:assert/strict';
import { existsSync, lstatSync, readFileSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';

export const basePath = '/cerbia/';

export function safeFile(root, parts) {
  const absolute = resolve(root, ...parts);
  const rel = relative(resolve(root), absolute);
  assert.ok(rel && rel !== '..' && !rel.startsWith(`..${sep}`) && !rel.startsWith(sep), `path escapes site: ${absolute}`);
  let parent = resolve(root);
  assert.ok(existsSync(parent) && lstatSync(parent).isDirectory() && !lstatSync(parent).isSymbolicLink(), `unsafe site directory: ${parent}`);
  for (const part of parts) {
    parent = join(parent, part);
    if (existsSync(parent)) assert.ok(!lstatSync(parent).isSymbolicLink(), `symlink in site path: ${parent}`);
  }
  return absolute;
}

export function routes(manifestPath, contractPath) {
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const contract = JSON.parse(readFileSync(contractPath, 'utf8'));
  assert.equal(contract.basePath, basePath);
  assert.equal(contract.artifactMount, basePath);
  assert.equal(manifest.routes.length, 38, 'expected 38 legacy routes');
  assert.equal(contract.legacyAliases.length, 38, 'expected 38 declared aliases');
  assert.equal(new Set(contract.legacyAliases).size, 38, 'duplicate contract alias');
  assert.deepEqual(new Set(manifest.routes.map((row) => row.oldUrl)), new Set(contract.legacyAliases), 'manifest and URL contract differ');
  const aliases = new Set();
  const declaredModules = new Set(['main', ...manifest.navigation.packageModules]);
  return manifest.routes.map((row) => {
    assert.match(row.oldUrl, /^\/cerbia\/docs\/(?:[a-z0-9-]+\/)*$/, `unsafe legacy route: ${row.oldUrl}`);
    assert.ok(!aliases.has(row.oldUrl), `duplicate legacy route: ${row.oldUrl}`);
    aliases.add(row.oldUrl);
    assert.equal(row.redirectTarget, row.targetPageId, `stale redirect: ${row.oldUrl}`);
    const [module, page, extra] = row.targetPageId.split(':');
    assert.equal(extra, undefined, `invalid target: ${row.oldUrl}`);
    assert.ok(declaredModules.has(module) && module === row.targetModule, `unknown target module: ${row.oldUrl}`);
    assert.match(page, /^(?:[a-z0-9-]+\/)*[a-z0-9-]+$/, `unsafe target page: ${row.oldUrl}`);
    const targetParts = [module, ...(page === 'index' ? [] : page.split('/')), 'index.html'];
    const aliasParts = [...row.oldUrl.slice(basePath.length).split('/').filter(Boolean), 'index.html'];
    return { oldUrl: row.oldUrl, aliasParts, targetParts, targetPageId: row.targetPageId };
  });
}

export function selectedVersion(site, mappedRoutes) {
  const hasStable = existsSync(safeFile(site, ['stable', 'index.html']));
  const version = hasStable ? 'stable' : 'prerelease';
  assert.ok(existsSync(safeFile(site, [version, 'index.html'])), `missing ${version} marketing page`);
  for (const route of mappedRoutes) {
    const target = safeFile(site, [version, ...route.targetParts]);
    assert.ok(existsSync(target) && lstatSync(target).isFile(), `missing canonical target: ${target}`);
    const html = readFileSync(target, 'utf8');
    assert.match(html, /<main\b[\s\S]*?<h1\b/i, `empty canonical page: ${target}`);
    assert.match(html, /<nav class="side-menu__nav"[\s\S]*?aria-current="page"/, `target absent from rendered navigation: ${target}`);
  }
  return version;
}

export function aliasHtml(target) {
  assert.match(target, /^\/cerbia\/(?:stable|prerelease)\/(?:[a-z0-9-]+\/)*$/);
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Documentation moved · CerbIA</title></head>
<body><main><h1>Documentation moved</h1><p>Continue to <a href="${target}">the CerbIA documentation page</a>.</p>
<noscript><p>JavaScript is unavailable. <a href="${target}">Open the CerbIA documentation page</a>.</p></noscript></main>
<script>const destination = new URL(${JSON.stringify(target)}, location.origin);
destination.search = location.search;
destination.hash = location.hash;
location.replace(destination.href);</script></body></html>
`;
}
