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

// Tokenize tags with quote-aware boundaries: `data-x=" aria-labelledby=..."`
// is one attribute value, not another SVG attribute or an HTML element.
const tagPattern = /<\/?[a-z][\w:-]*(?:[^>"']|"[^"]*"|'[^']*')*>/gi;

function tagAttributes(tag) {
  const attributes = new Map();
  const open = tag.match(/^<[a-z][\w:-]*/i)?.[0].length ?? 0;
  const source = tag.slice(open, -1);
  const pattern = /\s([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/gy;
  let index = 0;
  while (index < source.length) {
    if (source.slice(index).trim() === '' || source.slice(index).trim() === '/') break;
    pattern.lastIndex = index;
    const attribute = pattern.exec(source);
    assert.ok(attribute, `malformed HTML attribute in ${tag.slice(0, 80)}`);
    assert.ok(!attributes.has(attribute[1]), `duplicate HTML attribute: ${attribute[1]}`);
    attributes.set(attribute[1], attribute[2] ?? attribute[3] ?? attribute[4] ?? '');
    index = pattern.lastIndex;
  }
  return attributes;
}

function svgTextNode(content, name) {
  const tags = [...content.matchAll(tagPattern)];
  let depth = 0;
  for (let index = 0; index < tags.length; index += 1) {
    const tag = tags[index];
    const closing = tag[0].startsWith('</');
    const tagName = tag[0].match(/^<\/?([\w:-]+)/)?.[1]?.toLowerCase();
    if (closing) {
      depth -= 1;
    } else if (depth === 0 && tagName === name) {
      const next = tags[index + 1];
      if (next?.[0].toLowerCase() === `</${name}>`) {
        return { id: tagAttributes(tag[0]).get('id'), text: content.slice(tag.index + tag[0].length, next.index).trim() };
      }
    }
    if (!closing && !tag[0].endsWith('/>')) depth += 1;
  }
  return undefined;
}

function renderedDiagrams(html, context) {
  // Comments and script/template content are not rendered SVG nodes. Replace
  // with a space so markup on either side cannot be joined into a fake tag.
  const rendered = html.replace(/<!--[\s\S]*?-->|<(script|template|style)\b(?:[^>"']|"[^"]*"|'[^']*')*>[\s\S]*?<\/\1\s*>/gi, ' ')
    .replace(tagPattern, (tag) => tag.replace(/=("[^"]*"|'[^']*')/g,
      (attribute) => attribute.replaceAll('<', '&lt;').replaceAll('>', '&gt;')));
  const ids = [...rendered.matchAll(tagPattern)].filter(([tag]) => !tag.startsWith('</') && /\sid\s*=/.test(tag))
    .map(([tag]) => tagAttributes(tag).get('id')).filter(Boolean);
  assert.equal(new Set(ids).size, ids.length, `${context}: duplicate HTML id`);
  const containers = [...rendered.matchAll(tagPattern)]
    .filter(([tag]) => /^<div\b/i.test(tag))
    .filter(([tag]) => {
      const attrs = tagAttributes(tag);
      return attrs.get('class')?.split(/\s+/).includes('docouture-diagram') && attrs.get('data-diagram-type') === 'mermaid';
    })
    .map((tag) => rendered.slice(tag.index + tag[0].length).match(/^([\s\S]*?)<\/div><\/div>/)?.[1] ?? '');
  return containers.map((body, index) => {
    const tags = [...body.matchAll(tagPattern)];
    const svgIndex = tags.findIndex(([tag]) => /^<svg\b/i.test(tag));
    if (svgIndex !== -1) {
      const root = tags[svgIndex];
      const end = tags.slice(svgIndex + 1).find(([tag]) => /^<\/svg\s*>$/i.test(tag));
      assert.ok(end, `${context} diagram ${index + 1}: missing rendered SVG close tag`);
      const content = body.slice(root.index + root[0].length, end.index);
      const titleNode = svgTextNode(content, 'title');
      const descriptionNode = svgTextNode(content, 'desc');
      const title = titleNode?.text;
      const description = descriptionNode?.text;
      const rootAttributes = tagAttributes(root[0]);
      const labelledBy = rootAttributes.get('aria-labelledby')?.trim().split(/\s+/) ?? [];
      const describedBy = rootAttributes.get('aria-describedby')?.trim().split(/\s+/) ?? [];
      const titleId = titleNode?.id;
      const descriptionId = descriptionNode?.id;
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
