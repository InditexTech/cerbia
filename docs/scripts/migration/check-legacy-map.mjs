import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { frozenSource, frozenSourcePaths } from './frozen-source.mjs';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const defaultManifest = join(repoRoot, 'docs/scripts/migration/legacy-routes.json');
const defaultSourceRoot = join(repoRoot, 'docs/content/docs');
const args = process.argv.slice(2);
const modes = ['--source-check', '--map-only', '--nav'];
const failurePrefix = args.includes('--nav') ? 'NAV_CHECK_FAILED' : args.includes('--map-only') ? 'MAP_ONLY_FAILED' : 'SOURCE_CHECK_FAILED';

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const sourceRoot = option('--source-root', defaultSourceRoot);
const manifestPath = option('--manifest', defaultManifest);
const contentRoot = option('--content-root', join(repoRoot, 'docs/src'));

function assertNav(manifest, allowPendingTargets) {
  const antoraPath = join(contentRoot, 'antora.yml');
  const descriptor = readFileSync(antoraPath, 'utf8');
  const expectedModules = ['main', ...manifest.navigation.packageModules];
  const registeredNavs = [...descriptor.matchAll(/^  - modules\/([^/]+)\/nav\.adoc$/gm)]
    .map(([, module]) => `modules/${module}/nav.adoc`);
  const expectedNavs = expectedModules.map((module) => `modules/${module}/nav.adoc`);
  assert.deepEqual(registeredNavs, expectedNavs, 'Antora must register main and six package nav files in order');

  const registeredModules = [...descriptor.matchAll(/^  - module: ([a-z0-9-]+)$/gm)]
    .map(([, module]) => module);
  assert.deepEqual(registeredModules, expectedModules, 'Antora nav_modules must register main and six package modules in order');
  assert.match(descriptor, /^not_found_module: main$/m, '404 page module must be main');
  assert.match(descriptor, /^footer:\n  groups:/m, 'component footer groups must be configured');

  const sectionNames = manifest.navigation.mainSections.map(({ name }) => name);
  const mainNavPath = join(contentRoot, 'modules/main/nav.adoc');
  const mainNav = readFileSync(mainNavPath, 'utf8');
  const navGroups = new Map();
  const actualSections = [];
  let activeSection;
  for (const line of mainNav.split(/\r?\n/)) {
    const item = line.match(/^\* (.+)$/)?.[1];
    if (!item) continue;
    if (!item.startsWith('xref:')) {
      activeSection = item;
      actualSections.push(item);
      continue;
    }
    const page = item.match(/^xref:([^\[]+)\.adoc\[/)?.[1];
    if (page) navGroups.set(`main:${page}`, activeSection);
  }
  assert.deepEqual(actualSections, sectionNames, 'main nav must declare the six section groups in order');

  const declaredTargets = new Map();
  const declaredOrder = new Map();
  for (const module of expectedModules) {
    const navPath = join(contentRoot, `modules/${module}/nav.adoc`);
    const nav = readFileSync(navPath, 'utf8');
    for (const [, page, label] of nav.matchAll(/xref:([^\[]+)\.adoc\[([^\]]*)\]/g)) {
      const pageId = `${module}:${page}`;
      declaredTargets.set(pageId, (declaredTargets.get(pageId) ?? 0) + 1);
      if (!declaredOrder.has(module)) declaredOrder.set(module, []);
      declaredOrder.get(module).push(pageId);
      if (!allowPendingTargets) {
        assert.ok(existsSync(join(contentRoot, `modules/${module}/pages/${page}.adoc`)), `missing nav target page: ${pageId}`);
      }
      assert.ok(label.trim().length > 0, `nav target has no label: ${pageId}`);
    }
  }

  const expectedTargets = manifest.routes.map(({ targetPageId }) => targetPageId);
  const sectionEntryIds = manifest.navigation.mainSections.map(({ entryPageId }) => entryPageId);
  for (const pageId of new Set([...expectedTargets, ...sectionEntryIds])) {
    assert.equal(declaredTargets.get(pageId), 1, `expected target exactly once in nav: ${pageId}`);
  }
  for (const row of manifest.routes.filter(({ targetModule }) => targetModule === 'main')) {
    assert.equal(navGroups.get(row.targetPageId), row.nav.group, `mapped page is in the wrong section: ${row.targetPageId}`);
  }
  for (const section of manifest.navigation.mainSections) {
    assert.equal(navGroups.get(section.entryPageId), section.name, `section entry is in the wrong group: ${section.entryPageId}`);
  }
  for (const pageId of declaredTargets.keys()) {
    assert.ok(expectedTargets.includes(pageId) || sectionEntryIds.includes(pageId), `unmapped nav target: ${pageId}`);
  }
  for (const module of expectedModules) {
    const mappedInManifestOrder = module === 'main'
      ? manifest.navigation.mainSections.flatMap(({ name }) => manifest.routes
          .filter(({ targetModule, nav }) => targetModule === module && nav.group === name)
          .sort((left, right) => left.nav.order - right.nav.order)
          .map(({ targetPageId }) => targetPageId))
      : manifest.routes
        .filter(({ targetModule }) => targetModule === module)
        .sort((left, right) => left.nav.order - right.nav.order)
        .map(({ targetPageId }) => targetPageId);
    const mappedInNavOrder = declaredOrder.get(module).filter((pageId) => expectedTargets.includes(pageId));
    assert.deepEqual(mappedInNavOrder, mappedInManifestOrder, `mapped nav order changed: ${module}`);
  }
}

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
  const flags = args.filter((arg) => arg.startsWith('--') && !['--manifest', '--source-root', '--content-root'].includes(arg));
  assert.ok(flags.length === 1 || (flags.length === 2 && flags.includes('--nav') && flags.includes('--allow-pending-targets')),
    'choose exactly one mode; --allow-pending-targets is only valid with --nav');
  assert.ok(modes.includes(flags[0]), `unsupported mode: ${flags[0]}`);
  assert.ok(!args.includes('--allow-pending-targets') || flags[0] === '--nav', '--allow-pending-targets is only valid with --nav');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));

  if (flags[0] === '--map-only') {
    assertMap(manifest);
    console.log(`MAP_ONLY_OK sources=${manifest.routes.length} mainSections=${manifest.navigation.mainSections.length} packageModules=${manifest.navigation.packageModules.length}`);
    process.exit(0);
  }

  if (flags[0] === '--nav') {
    assertMap(manifest);
    assertNav(manifest, args.includes('--allow-pending-targets'));
    console.log(`NAV_CHECK_OK sources=${manifest.routes.length} mainSections=${manifest.navigation.mainSections.length} packageModules=${manifest.navigation.packageModules.length} pendingTargets=${args.includes('--allow-pending-targets')}`);
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
    const contents = frozenSource(repoRoot, row, sourceRoot);
    const lines = contents.split('\n');
    assert.equal(row.lineCount, lines.at(-1) === '' ? lines.length - 1 : lines.length, `stale line count: ${row.source}`);
    lines.forEach((line, index) => {
      if (/^\s*```mermaid\s*$/.test(line)) {
        diagrams.push({ source: row.source, line: index + 1, fenceSha256: sha256(line) });
      }
    });
  }

  const actual = frozenSourcePaths(repoRoot, sourceRoot);
  assert.deepEqual([...sources].sort(), actual.sort(), 'missing or extra MDX source in frozen inventory');
  assert.equal(diagrams.length, 6, 'expected six Mermaid fences');
  assert.deepEqual(manifest.mermaidFences, diagrams, 'Mermaid fence locations changed');
  assert.equal(manifest.marketingHome.source, 'docs/app/page.tsx');
  frozenSource(repoRoot, manifest.marketingHome);
  assert.equal(manifest.marketingHome.oldUrl, '/cerbia/');
  assert.ok(!urls.has(manifest.marketingHome.oldUrl), 'marketing home must be separate from docs index');
  console.log(`SOURCE_CHECK_OK sources=${sources.size} oldUrls=${urls.size} mermaidFences=${diagrams.length}`);
} catch (error) {
  console.error(`${failurePrefix}: ${error.message}`);
  process.exitCode = 1;
}
