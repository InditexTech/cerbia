import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const defaultManifest = join(repoRoot, 'docs/scripts/migration/legacy-routes.json');
const defaultSourceRoot = join(repoRoot, 'docs/content/docs');
const args = process.argv.slice(2);
const modes = ['--source-check', '--map-only'];
const failurePrefix = args.includes('--map-only') ? 'MAP_ONLY_FAILED' : 'SOURCE_CHECK_FAILED';

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function walk(directory, extension) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return walk(path, extension);
    return entry.isFile() && entry.name.endsWith(extension) ? [path] : [];
  });
}

const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const sourceRoot = option('--source-root', defaultSourceRoot);
const manifestPath = option('--manifest', defaultManifest);

function assertMap(manifest) {
  const expectedSections = [
    'Overview',
    'Getting started',
    'Guides',
    'Reference',
    'Additional information',
    'Contributing',
  ];
  const expectedModules = [
    'cerbia',
    'cerbia-core',
    'cerbia-cli',
    'cerbia-ml',
    'cerbia-presidio',
    'cerbia-protectai',
  ];
  const sections = manifest.navigation?.mainSections;
  const modules = manifest.navigation?.packageModules;

  assert.deepEqual(sections?.map(({ name }) => name), expectedSections, 'main nav must have six ordered sections');
  assert.deepEqual(sections.map(({ order }) => order), [1, 2, 3, 4, 5, 6], 'main nav section order changed');
  assert.deepEqual(sections.map(({ entryPageId }) => entryPageId), [
    'main:about',
    'main:prerequisites',
    'main:guides-overview',
    'main:reference-overview',
    'main:additional-information',
    'main:contributing',
  ], 'main nav entry pages changed');
  assert.deepEqual(modules, expectedModules, 'package module list changed');
  assert.equal(manifest.routes.length, 38, 'expected 38 mapped sources');

  const targets = new Set();
  const mappedSources = new Set();
  const oldUrls = new Set();
  const sourceCounts = { root: 0, components: 0, packages: 0 };
  const moduleCounts = new Map(expectedModules.map((module) => [module, 0]));
  const navOrders = new Set();

  for (const row of manifest.routes) {
    for (const key of ['targetPageId', 'targetModule', 'nav', 'redirectTarget', 'pageFamily', 'order']) {
      assert.ok(Object.hasOwn(row, key), `missing mapping field ${key}: ${row.source}`);
    }

    assert.equal(typeof row.targetPageId, 'string', `missing target page ID: ${row.source}`);
    assert.equal(typeof row.targetModule, 'string', `missing target module: ${row.source}`);
    assert.ok(!mappedSources.has(row.source), `duplicate mapped source: ${row.source}`);
    mappedSources.add(row.source);
    const sourceGroup = row.source.match(/^docs\/content\/docs\/(components|packages)\//)?.[1] ?? 'root';
    sourceCounts[sourceGroup === 'components' ? 'components' : sourceGroup === 'packages' ? 'packages' : 'root'] += 1;
    assert.ok(!oldUrls.has(row.oldUrl), `duplicate mapped old URL: ${row.oldUrl}`);
    oldUrls.add(row.oldUrl);
    assert.match(row.targetPageId, new RegExp(`^${row.targetModule}:[a-z0-9/-]+$`), `invalid target page ID: ${row.source}`);
    assert.ok(!targets.has(row.targetPageId), `duplicate target page ID: ${row.targetPageId}`);
    targets.add(row.targetPageId);
    assert.equal(row.redirectTarget, row.targetPageId, `redirect target must identify mapped page: ${row.source}`);
    assert.match(row.pageFamily, /^(overview|architecture|quickstart|guide|reference|component-catalog|component-reference|package-gateway|package-landing)$/,
      `invalid page family: ${row.source}`);
    assert.ok(Number.isInteger(row.order) && row.order > 0, `invalid nav order: ${row.source}`);
    assert.equal(typeof row.nav?.group, 'string', `missing nav group: ${row.source}`);
    assert.equal(row.nav.order, row.order, `nav position mismatch: ${row.source}`);

    const navGroup = row.targetModule === 'main'
      ? expectedSections.includes(row.nav.group)
      : expectedModules.includes(row.nav.group);
    assert.ok(navGroup, `unknown nav group ${row.nav.group}: ${row.source}`);
    const navKey = `${row.targetModule}:${row.nav.group}:${row.order}`;
    assert.ok(!navOrders.has(navKey), `duplicate nav order ${navKey}`);
    navOrders.add(navKey);

    if (row.targetModule === 'main') {
      assert.ok(expectedSections.includes(row.nav.group), `main page outside a main section: ${row.source}`);
      assert.match(row.targetPageId, /^main:/, `main target has wrong module: ${row.source}`);
    } else {
      assert.ok(moduleCounts.has(row.targetModule), `unmapped package module: ${row.targetModule}`);
      assert.equal(row.nav.group, row.targetModule, `package page nav must match its module: ${row.source}`);
      assert.match(row.targetPageId, new RegExp(`^${row.targetModule}:`), `package target module mismatch: ${row.source}`);
      moduleCounts.set(row.targetModule, moduleCounts.get(row.targetModule) + 1);
    }
  }

  for (const [module, count] of moduleCounts) {
    assert.ok(count > 0, `package module has no mapped source: ${module}`);
  }
  assert.deepEqual(sourceCounts, { root: 8, components: 23, packages: 7 }, 'source group counts changed');
  for (const [module, group] of [
    ['main', expectedSections[0]],
    ['main', expectedSections[1]],
    ['main', expectedSections[3]],
    ...expectedModules.map((name) => [name, name]),
  ]) {
    const orders = manifest.routes
      .filter(({ targetModule, nav }) => targetModule === module && nav.group === group)
      .map(({ order }) => order)
      .sort((left, right) => left - right);
    const sectionEntry = module === 'main' ? sections.find(({ name }) => name === group) : null;
    const entryIsMapped = sectionEntry && manifest.routes.some(({ targetPageId }) => targetPageId === sectionEntry.entryPageId);
    const firstOrder = sectionEntry ? (entryIsMapped ? 1 : 2) : 1;
    assert.deepEqual(orders, Array.from({ length: orders.length }, (_, index) => index + firstOrder), `non-contiguous nav order: ${module}/${group}`);
  }

  const home = manifest.marketingHome;
  assert.equal(home.source, 'docs/app/page.tsx');
  assert.equal(home.oldUrl, '/cerbia/');
  assert.equal(home.targetPageId, 'ROOT:index');
  assert.equal(home.targetModule, 'ROOT');
  assert.equal(home.redirectTarget, home.targetPageId);
  assert.equal(home.pageFamily, 'marketing-home');
  assert.equal(home.order, 1);
  assert.deepEqual(home.nav, { group: 'Home', order: 1 });
  assert.ok(!manifest.routes.some(({ targetPageId }) => targetPageId === home.targetPageId), 'marketing home must be a separate target');
  assert.ok(!manifest.routes.some(({ oldUrl }) => oldUrl === home.oldUrl), 'marketing home URL must be separate from docs index');
  assert.equal(manifest.routes.find(({ source }) => source === 'docs/content/docs/index.mdx')?.oldUrl, '/cerbia/docs/',
    'docs index must remain distinct from marketing home');
}

try {
  const flags = args.filter((arg) => arg.startsWith('--') && !['--manifest', '--source-root'].includes(arg));
  assert.equal(flags.length, 1, 'choose exactly one of --source-check or --map-only');
  assert.ok(modes.includes(flags[0]), `unsupported mode: ${flags[0]}`);
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

  if (flags[0] === '--map-only') {
    assertMap(manifest);
    console.log(`MAP_ONLY_OK sources=${manifest.routes.length} mainSections=${manifest.navigation.mainSections.length} packageModules=${manifest.navigation.packageModules.length}`);
    process.exit(0);
  }

  assert.equal(manifest.routes.length, 38, 'expected 38 authored sources');
  const sources = new Set();
  const urls = new Set();
  const diagrams = [];

  for (const row of manifest.routes) {
    assert.equal(typeof row.source, 'string');
    assert.match(row.source, /^docs\/content\/docs\/(?:[a-z0-9-]+\/)*[a-z0-9-]+\.mdx$/);
    assert.ok(!sources.has(row.source), `duplicate source: ${row.source}`);
    sources.add(row.source);
    assert.equal(typeof row.oldUrl, 'string');
    assert.ok(!urls.has(row.oldUrl), `duplicate old URL: ${row.oldUrl}`);
    urls.add(row.oldUrl);
    const relativeSource = relative('docs/content/docs', row.source).replaceAll(sep, '/');
    const slug = relativeSource.replace(/(?:^|\/)index\.mdx$/, '').replace(/\.mdx$/, '');
    const oldUrl = `/cerbia/docs/${slug ? `${slug}/` : ''}`;
    assert.equal(row.oldUrl, oldUrl, `unexpected old URL: ${row.source}`);
    assert.deepEqual(row.oldUrlVariants, [oldUrl.slice(0, -1), `${oldUrl}index.html`]);
    for (const key of ['targetPageId', 'targetModule', 'nav', 'redirectTarget']) {
      assert.ok(Object.hasOwn(row, key), `missing reserved field: ${key}`);
    }
    const file = join(sourceRoot, relativeSource);
    assert.ok(existsSync(file), `missing source file: ${row.source}`);
    const contents = readFileSync(file);
    assert.equal(row.sha256, sha256(contents), `stale source hash: ${row.source}`);
    const lines = contents.toString('utf8').split('\n');
    assert.equal(row.lineCount, lines.at(-1) === '' ? lines.length - 1 : lines.length, `stale line count: ${row.source}`);
    lines.forEach((line, index) => {
      if (/^\s*```mermaid\s*$/.test(line)) {
        diagrams.push({ source: row.source, line: index + 1, fenceSha256: sha256(line) });
      }
    });
  }

  const actual = walk(sourceRoot, '.mdx').map((path) => `docs/content/docs/${relative(sourceRoot, path).split(sep).join('/')}`);
  assert.deepEqual([...sources].sort(), actual.sort(), 'missing or extra MDX source in frozen inventory');
  assert.equal(diagrams.length, 6, 'expected six Mermaid fences');
  assert.deepEqual(manifest.mermaidFences, diagrams, 'Mermaid fence locations changed');
  assert.equal(manifest.marketingHome.source, 'docs/app/page.tsx');
  assert.equal(manifest.marketingHome.oldUrl, '/cerbia/');
  assert.ok(!urls.has(manifest.marketingHome.oldUrl), 'marketing home must be separate from docs index');
  console.log(`SOURCE_CHECK_OK sources=${sources.size} oldUrls=${urls.size} mermaidFences=${diagrams.length}`);
} catch (error) {
  console.error(`${failurePrefix}: ${error.message}`);
  process.exitCode = 1;
}
