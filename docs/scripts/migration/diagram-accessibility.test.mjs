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
