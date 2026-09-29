import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const svg = (n) => `<div class="docouture-diagram" data-diagram-type="mermaid"><div><svg id="docouture-diagram-${n}-container" aria-labelledby="docouture-diagram-${n}-chart-title-container" aria-describedby="docouture-diagram-${n}-chart-desc-container"><title id="docouture-diagram-${n}-chart-title-container">Diagram ${n}</title><desc id="docouture-diagram-${n}-chart-desc-container">Meaningful description for diagram ${n}</desc></svg></div></div>`;

test('Given repeated diagrams, when checking an artifact, then only exact unique title and desc IDREFs pass', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-accessibility-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  const check = () => spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--version', 'prerelease', '--page-id', 'main:architecture'], { encoding: 'utf8' });
  writeFileSync(page, svg(1) + svg(2));
  assert.equal(check().status, 0);

  writeFileSync(page, (svg(1) + svg(2)).replace('aria-labelledby="docouture-diagram-2-chart-title-container"', 'aria-labelledby="chart-title-container"'));
  assert.match(check().stderr, /aria-labelledby must resolve exactly/);
  assert.equal(check().status, 1);

  writeFileSync(page, (svg(1) + svg(2)).replace('aria-describedby="docouture-diagram-2-chart-desc-container"', 'aria-describedby="chart-desc-container"'));
  assert.match(check().stderr, /aria-describedby must resolve exactly/);
  assert.equal(check().status, 1);

  writeFileSync(page, svg(1) + svg(1));
  assert.match(check().stderr, /duplicate HTML id/);
  assert.equal(check().status, 1);

  writeFileSync(page, '<div class="docouture-diagram" data-diagram-type="mermaid"><div><pre>raw Mermaid after 503</pre></div></div>');
  assert.match(check().stderr, /missing rendered SVG\/image/);
  assert.equal(check().status, 1);
});

test('Given only data-aria attributes, when checking an SVG, then missing real ARIA IDREFs fail', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-data-aria-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  writeFileSync(page, svg(1).replaceAll(' aria-labelledby=', ' data-aria-labelledby=').replaceAll(' aria-describedby=', ' data-aria-describedby='));
  const result = spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--page-id', 'main:architecture'], { encoding: 'utf8' });
  assert.equal(result.status, 1, `data-aria-* is not accessible: ${result.stdout}${result.stderr}`);
  assert.match(result.stderr, /aria-labelledby/);
});

test('Given comment-only title and desc, when checking an SVG, then missing DOM nodes fail', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-comment-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  writeFileSync(page, svg(1).replace(/(<title\b[\s\S]*?<\/desc>)/, '<!-- $1 -->'));
  const result = spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--page-id', 'main:architecture'], { encoding: 'utf8' });
  assert.equal(result.status, 1, `commented nodes are not accessible: ${result.stdout}${result.stderr}`);
  assert.match(result.stderr, /aria-labelledby/);
});

test('Given inert script or template diagrams and attribute-value spoofing, when checking a page, then no rendered diagram is counted', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-inert-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  const check = () => spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--page-id', 'main:architecture'], { encoding: 'utf8' });
  for (const hidden of [`<script type="text/plain">${svg(1)}</script>`, `<template>${svg(1)}</template>`,
    `<script data-hint="a > b" type="text/plain">${svg(1)}</script>`,
    `<style data-hint="a > b">${svg(1)}</style>`,
    `<div data-spoof='${svg(1)}'></div>`, `<!-- ${svg(1)} -->`,
    svg(1).replace('class="docouture-diagram"', 'data-class="docouture-diagram"')]) {
    writeFileSync(page, hidden);
    const result = check();
    assert.equal(result.status, 1, `inert markup was counted: ${result.stdout}${result.stderr}`);
    assert.match(result.stderr, /contains no rendered Mermaid diagrams/);
  }
});

test('Given quoted lookalike attribute names and nested title nodes, when checking an SVG, then only its real own labels count', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-spoof-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  const check = () => spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--page-id', 'main:architecture'], { encoding: 'utf8' });
  for (const hidden of [
    svg(1).replace(' aria-labelledby=', ' data-hint=" aria-labelledby=spoof" data-aria-labelledby='),
    svg(1).replace(/(<title\b[\s\S]*?<\/title>)/, '<g>$1</g>'),
    svg(1).replace(' aria-labelledby=', ' aria-labelledby="other" aria-labelledby='),
  ]) {
    writeFileSync(page, hidden);
    const result = check();
    assert.equal(result.status, 1, `lookalike label was counted: ${result.stdout}${result.stderr}`);
    assert.match(result.stderr, /aria-labelledby/);
  }
});

test('Given misleading SVG tag delimiters inside quoted attributes, when checking, then the actual SVG labels still pass', (t) => {
  const site = mkdtempSync(join(tmpdir(), 'cerbia-diagram-quoted-'));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  const page = join(site, 'prerelease/main/architecture/index.html');
  mkdirSync(dirname(page), { recursive: true });
  writeFileSync(page, svg(1).replace('<svg id=', '<svg data-hint="not > a close tag" id='));
  const result = spawnSync(process.execPath, [join(here, 'check-diagrams.mjs'), '--mode', 'sample', '--site-dir', site, '--page-id', 'main:architecture'], { encoding: 'utf8' });
  assert.equal(result.status, 0, `${result.stdout}${result.stderr}`);
});

test('Given namespaced Kroki markup, when the site postprocessor runs, then it repairs only root IDREF attributes', () => {
  const { repairDiagramIdrefs } = requireExtension();
  const broken = svg(1).replace('aria-labelledby="docouture-diagram-1-chart-title-container"', 'aria-labelledby="chart-title-container"')
    .replace('aria-describedby="docouture-diagram-1-chart-desc-container"', 'aria-describedby="chart-desc-container"');
  const second = svg(2).replace('aria-labelledby="docouture-diagram-2-chart-title-container"', 'aria-labelledby="chart-title-container"')
    .replace('aria-describedby="docouture-diagram-2-chart-desc-container"', 'aria-describedby="chart-desc-container"');
  const output = repairDiagramIdrefs(broken + second);
  assert.equal(output, svg(1) + svg(2));
  assert.equal(repairDiagramIdrefs(output), output);
  const unrelated = '<svg id="other"><title id="title">A title</title><desc id="desc">A description</desc></svg>';
  assert.equal(repairDiagramIdrefs(unrelated), unrelated);
});

function requireExtension() {
  return require(join(here, 'diagram-accessibility.cjs'));
}
