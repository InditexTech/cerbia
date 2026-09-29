#!/usr/bin/env node

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const defaults = {
  inventory: join(repoRoot, 'docs/scripts/migration/diagram-inventory.json'),
  routes: join(repoRoot, 'docs/scripts/migration/legacy-routes.json'),
  siteDir: join(repoRoot, 'docs/build/site'),
};

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    assert.ok(argument.startsWith('--'), `unexpected argument: ${argument}`);
    const name = argument.slice(2);
    assert.ok(['mode', 'site-dir', 'version', 'page-id', 'inventory', 'routes'].includes(name), `unknown option: ${argument}`);
    assert.ok(!Object.hasOwn(options, name), `duplicate option: ${argument}`);
    const value = argv[index + 1];
    assert.ok(value && !value.startsWith('--'), `missing value for ${argument}`);
    options[name] = value;
    index += 1;
  }
  assert.ok(options.mode === 'sample' || options.mode === 'full', 'usage: check-diagrams.mjs --mode sample|full --site-dir DIR [--version prerelease|stable] [--page-id MODULE:PAGE]');
  options['site-dir'] ??= defaults.siteDir;
  options.version ??= 'prerelease';
  assert.match(options.version, /^[a-zA-Z0-9._-]+$/, 'invalid --version');
  options.siteDir = resolve(options['site-dir']);
  options.pageId = options['page-id'];
  if (options.mode === 'sample') {
    assert.ok(options.pageId, 'sample mode requires an explicit --page-id');
    assert.match(options.pageId, /^[A-Za-z0-9_-]+:[A-Za-z0-9_./-]+$/, 'invalid sample --page-id');
  } else {
    assert.ok(!options.pageId, 'full mode derives every page from the manifest; do not pass --page-id');
  }
  options.inventoryPath = resolve(options.inventory || defaults.inventory);
  options.routesPath = resolve(options.routes || defaults.routes);
  return options;
}

function outputPath(siteDir, version, pageId) {
  const separator = pageId.indexOf(':');
  assert.ok(separator > 0, `invalid page ID: ${pageId}`);
  const module = pageId.slice(0, separator);
  const page = pageId.slice(separator + 1);
  const parts = module === 'ROOT'
    ? [siteDir, version, ...page.split('/'), 'index.html']
    : [siteDir, version, module, ...page.split('/'), 'index.html'];
  const result = resolve(...parts);
  assert.ok(result.startsWith(`${resolve(siteDir)}${sep}`), `page ID escaped the output directory: ${pageId}`);
  return result;
}

function renderedDiagrams(html, context) {
  const ids = [...html.matchAll(/\sid=["']([^"']+)["']/g)].map(([, id]) => id);
  assert.equal(new Set(ids).size, ids.length, `${context}: duplicate HTML id`);
  const containers = [...html.matchAll(/<div\b(?=[^>]*\bclass="[^"]*\bdocouture-diagram\b[^"]*")(?=[^>]*\bdata-diagram-type="mermaid")[^>]*>([\s\S]*?)<\/div><\/div>/g)];
  return containers.map(([, body], index) => {
    const svg = body.match(/<svg\b([^>]*)>([\s\S]*?)<\/svg>/);
    if (svg) {
      const [, attributes, content] = svg;
      const title = content.match(/<title\b[^>]*>([\s\S]*?)<\/title>/)?.[1]?.replace(/<[^>]*>/g, '').trim();
      const description = content.match(/<desc\b[^>]*>([\s\S]*?)<\/desc>/)?.[1]?.replace(/<[^>]*>/g, '').trim();
      const titleId = content.match(/<title\b[^>]*\bid="([^"]+)"/)?.[1];
      const descriptionId = content.match(/<desc\b[^>]*\bid="([^"]+)"/)?.[1];
      const labelledBy = attributes.match(/\baria-labelledby="([^"]+)"/)?.[1]?.split(/\s+/) ?? [];
      const describedBy = attributes.match(/\baria-describedby="([^"]+)"/)?.[1]?.split(/\s+/) ?? [];
      assert.ok(title && title.length >= 4 && titleId && labelledBy.length === 1 && labelledBy[0] === titleId,
        `${context} diagram ${index + 1}: aria-labelledby must resolve exactly to its own SVG title id`);
      assert.ok(description && description.length >= 12 && descriptionId && describedBy.length === 1 && describedBy[0] === descriptionId,
        `${context} diagram ${index + 1}: aria-describedby must resolve exactly to its own SVG desc id`);
      return { kind: 'svg', title, description };
    }

    const image = body.match(/<img\b([^>]*)>/);
    if (image) {
      const attributes = image[1];
      const alt = attributes.match(/\balt="([^"]*)"/)?.[1]?.trim();
      const src = attributes.match(/\bsrc="([^"]+)"/)?.[1];
      assert.ok(alt && alt.length >= 12, `${context} diagram ${index + 1}: image needs meaningful alt text`);
      assert.ok(src && /^data:image\/(?:png|jpeg|svg\+xml);base64,/.test(src), `${context} diagram ${index + 1}: image source is not an embedded rendered image`);
      return { kind: 'image', alt };
    }

    assert.fail(`${context} diagram ${index + 1}: missing rendered SVG/image; Kroki likely fell back to raw Mermaid source`);
  });
}

function readPage(siteDir, version, pageId) {
  const path = outputPath(siteDir, version, pageId);
  assert.ok(existsSync(path), `missing built page for ${pageId}: ${path}`);
  return { path, html: readFileSync(path, 'utf8') };
}

function runSample(options) {
  const { path, html } = readPage(options.siteDir, options.version, options.pageId);
  const diagrams = renderedDiagrams(html, `${options.pageId} (${path})`);
  assert.ok(diagrams.length > 0, `sample page ${options.pageId} contains no rendered Mermaid diagrams`);
  console.log(JSON.stringify({ mode: 'sample', fullInventoryVerified: false, pageId: options.pageId, renderedDiagramCount: diagrams.length, diagrams }, null, 2));
}

function runFull(options) {
  const inventory = JSON.parse(readFileSync(options.inventoryPath, 'utf8'));
  const routes = JSON.parse(readFileSync(options.routesPath, 'utf8'));
  assert.equal(inventory.expectedDiagramCount, 6, 'expected the frozen six-diagram source inventory');
  assert.equal(inventory.mermaidFences.length, inventory.expectedDiagramCount, 'inventory count mismatch');
  assert.deepEqual(inventory.mermaidFences, routes.mermaidFences, 'diagram inventory differs from the committed frozen source fence manifest');

  const byPage = new Map();
  for (const fence of inventory.mermaidFences) {
    const route = routes.routes.find((candidate) => candidate.source === fence.source);
    assert.ok(route?.targetPageId, `diagram source has no mapped target page: ${fence.source}`);
    const entries = byPage.get(route.targetPageId) ?? [];
    entries.push(fence);
    byPage.set(route.targetPageId, entries);
  }

  const results = [];
  for (const [pageId, fences] of byPage) {
    const { path, html } = readPage(options.siteDir, options.version, pageId);
    const diagrams = renderedDiagrams(html, `${pageId} (${path})`);
    assert.equal(diagrams.length, fences.length, `${pageId}: expected ${fences.length} rendered diagram(s) mapped from the frozen inventory; found ${diagrams.length}`);
    results.push({ pageId, sourceFences: fences.map(({ source, line }) => ({ source, line })), expected: fences.length, rendered: diagrams.length, diagrams });
  }

  const verified = results.reduce((total, page) => total + page.rendered, 0);
  assert.equal(verified, inventory.expectedDiagramCount, 'full inventory rendered count mismatch');
  console.log(JSON.stringify({ mode: 'full', fullInventoryVerified: true, version: options.version, expectedDiagramCount: inventory.expectedDiagramCount, renderedDiagramCount: verified, pages: results }, null, 2));
}

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.mode === 'sample') runSample(options);
  else runFull(options);
} catch (error) {
  console.error(`DIAGRAM_CHECK_FAILED: ${error.message}`);
  process.exitCode = 1;
}
