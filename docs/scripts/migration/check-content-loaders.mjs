#!/usr/bin/env node

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const expectedSources = new Map([
  ['docs/content/docs/components/custom-components/index.mdx', {
    id: 'main:components/custom-components', headings: ['Configuration and runtime model', 'Contract reference', 'Custom scanner example', 'Other component skeletons', 'Loader', 'Preprocessor', 'Score aggregator', 'Integration constraints'], code: 6, tables: 1,
  }],
  ['docs/content/docs/components/loaders/index.mdx', {
    id: 'main:components/loaders', headings: [], code: 0, tables: 0,
  }],
  ['docs/content/docs/components/loaders/text-loader.mdx', {
    id: 'main:components/loaders/text-loader', headings: ['Parameters'], code: 2, tables: 1,
  }],
  ['docs/content/docs/components/loaders/file-loader.mdx', {
    id: 'main:components/loaders/file-loader', headings: ['Parameters'], code: 1, tables: 1,
  }],
  ['docs/content/docs/components/preprocessors/index.mdx', {
    id: 'main:components/preprocessors', headings: [], code: 0, tables: 0,
  }],
  ['docs/content/docs/components/preprocessors/speculative-decoding.mdx', {
    id: 'main:components/preprocessors/speculative-decoding', headings: ['What it does', 'Configuration', 'Constructor parameters', 'Built-in decoders', 'Search, scoring, and acceptance', 'Attribution', 'Metadata and lineage', 'Limits and operational notes'], code: 4, tables: 3,
  }],
  ['docs/content/docs/components/preprocessors/whitespace-normalization.mdx', {
    id: 'main:components/preprocessors/whitespace-normalization', headings: ['Parameters'], code: 1, tables: 1,
  }],
]);
const expectedNav = new Map([
  ['main:components/custom-components', 'components/custom-components'],
  ['main:components/loaders', 'components/loaders'],
  ['main:components/loaders/text-loader', 'components/loaders/text-loader'],
  ['main:components/loaders/file-loader', 'components/loaders/file-loader'],
  ['main:components/preprocessors', 'components/preprocessors'],
  ['main:components/preprocessors/speculative-decoding', 'components/preprocessors/speculative-decoding'],
  ['main:components/preprocessors/whitespace-normalization', 'components/preprocessors/whitespace-normalization'],
]);

function parseArgs(argv) {
  const options = {};
  const flags = new Set();
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--content' || arg === '--allow-pending-targets') {
      assert.ok(!flags.has(arg), `duplicate option: ${arg}`);
      flags.add(arg);
      continue;
    }
    assert.ok(['--group', '--manifest', '--pages-dir'].includes(arg), `unsupported option: ${arg}`);
    assert.ok(!Object.hasOwn(options, arg), `duplicate option: ${arg}`);
    const value = argv[index + 1];
    assert.ok(value && !value.startsWith('--'), `missing value for ${arg}`);
    options[arg] = arg === '--group' ? value : resolve(value);
    index += 1;
  }
  assert.ok(flags.has('--content'), 'required mode: --content');
  assert.equal(options['--group'], 'loaders-preprocessors', 'required content group: loaders-preprocessors');
  options.allowPendingTargets = flags.has('--allow-pending-targets');
  options.manifestPath = options['--manifest'] ?? join(repoRoot, 'docs/scripts/migration/legacy-routes.json');
  options.pagesPath = options['--pages-dir'] ?? join(repoRoot, 'docs/src/modules/main/pages');
  return options;
}

function targetPagePath(pagesDir, pageId) {
  const match = pageId.match(/^([a-z][a-z0-9-]*):([a-z0-9/-]+)$/);
  assert.ok(match, `invalid manifest page ID: ${pageId}`);
  const [, module, page] = match;
  const path = resolve(pagesDir, `${page}.adoc`);
  assert.ok(path.startsWith(`${resolve(pagesDir)}/`), `page ID escapes pages directory: ${pageId}`);
  assert.ok(resolve(pagesDir).endsWith(`/modules/${module}/pages`), `page ID module does not match target directory: ${pageId}`);
  return path;
}

function parseSource(source) {
  const title = source.match(/^title:\s*["']?([^"'\n]+)["']?\s*$/m)?.[1];
  assert.ok(title, 'source page has no frontmatter title');
  const body = source.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  const headings = [...body.matchAll(/^#{1,6}\s+(.+?)\s*#*\s*$/gm)].map(([, heading]) => heading.trim());
  const codeBlocks = [...body.matchAll(/^```([\w+-]*)\s*\r?\n([\s\S]*?)^```\s*$/gm)].map(([, language, code]) => ({
    language: language.toLowerCase(),
    code: code.replaceAll('\r\n', '\n').trimEnd(),
  }));
  const tableRows = body.split(/\r?\n/)
    .filter((line) => /^\s*\|/.test(line) && !/^\s*\|\s*:?-{3,}/.test(line))
    .map(splitTableRow);
  return { title, headings, codeBlocks, tableRows };
}

function normalizeMarkup(value) {
  return value.replace(/`([^`]+)`/g, '$1').replace(/\*\*([^*]+)\*\*/g, '$1').replaceAll('\\|', '|').toLowerCase();
}

function splitTableRow(line) {
  const cells = [];
  let cell = '';
  let inCode = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '`') inCode = !inCode;
    if (char === '|' && !inCode && line[index - 1] !== '\\') {
      if (cell || cells.length > 0) cells.push(cell.trim());
      cell = '';
      continue;
    }
    cell += char;
  }
  if (cell.trim()) cells.push(cell.trim());
  return cells.filter(Boolean);
}

function assertSourceParity(source, target, sourcePath, targetId) {
  const sourceParts = parseSource(source);
  const targetHeadings = [...target.matchAll(/^={1,6}\s+(.+?)\s*$/gm)].map(([, heading]) => normalizeMarkup(heading.trim()));
  for (const heading of [sourceParts.title, ...sourceParts.headings]) {
    assert.ok(targetHeadings.includes(normalizeMarkup(heading)), `missing source heading in ${targetId}: ${heading}`);
  }
  const targetCodeBlocks = [...target.matchAll(/^\[source(?:,([^\]]+))?\]\s*\r?\n-{4,}\r?\n([\s\S]*?)\r?\n-{4,}\s*$/gm)].map(([, language = '', code]) => ({
    language: language.split(',')[0].toLowerCase(),
    code: code.replaceAll('\r\n', '\n').trimEnd(),
  }));
  const diagrams = [...sourceParts.codeBlocks.filter(({ language }) => language === 'mermaid')];
  const sourceCode = sourceParts.codeBlocks.filter(({ language }) => language !== 'mermaid');
  assert.equal(targetCodeBlocks.length, sourceCode.length, `code example count changed for ${sourcePath}`);
  for (const block of sourceCode) {
    assert.ok(targetCodeBlocks.some((candidate) => candidate.language === block.language && candidate.code === block.code),
      `missing or changed ${block.language || 'text'} code block in ${targetId} from ${sourcePath}`);
  }
  const targetTableRows = [...target.matchAll(/^\|===\s*\r?\n([\s\S]*?)^\|===\s*$/gm)]
    .flatMap(([, table]) => table.split(/\r?\n/).filter((line) => line.startsWith('|'))
      .map((line) => splitTableRow(line).map(normalizeMarkup)));
  for (const row of sourceParts.tableRows) {
    const normalized = row.map(normalizeMarkup);
    assert.ok(targetTableRows.some((candidate) => candidate.length === normalized.length && candidate.every((cell, index) => cell === normalized[index])),
      `missing source table row in ${targetId}: ${row.join(' | ')}`);
  }
  assert.ok(target.includes(`Source: ${sourcePath}`), `missing source traceability comment in ${targetId}`);
  return { sourceParts, sourceCodeCount: sourceCode.length, sourceTableRows: sourceParts.tableRows.length, diagramCount: diagrams.length };
}

function run() {
  const options = parseArgs(process.argv.slice(2));
  const manifest = JSON.parse(readFileSync(options.manifestPath, 'utf8'));
  const rows = manifest.routes.filter(({ source }) => expectedSources.has(source));
  assert.equal(rows.length, expectedSources.size, 'manifest must include each of the seven source pages exactly once');
  assert.deepEqual([...new Set(rows.map(({ source }) => source))].sort(), [...expectedSources.keys()].sort(), 'unexpected or duplicate source rows in task group');
  for (const row of rows) assert.match(row.targetPageId, /^main:[a-z0-9/-]+$/, `invalid manifest page ID: ${row.targetPageId}`);

  const allowedTargets = new Set([
    ...manifest.routes.map(({ targetPageId }) => targetPageId),
    ...(manifest.navigation?.mainSections ?? []).map(({ entryPageId }) => entryPageId),
  ]);
  const declaredModules = new Set(['main', ...(manifest.navigation?.packageModules ?? [])]);
  const nav = readFileSync(join(dirname(options.pagesPath), 'nav.adoc'), 'utf8');
  const sourceRoot = join(repoRoot, 'docs/content/docs');
  const results = [];

  for (const [source, contract] of expectedSources) {
    const matches = rows.filter((row) => row.source === source);
    assert.equal(matches.length, 1, `manifest source must occur once: ${source}`);
    const [row] = matches;
    assert.match(row.targetPageId, /^main:[a-z0-9/-]+$/, `invalid manifest page ID: ${row.targetPageId}`);
    assert.equal(row.targetPageId, contract.id, `stale mapping for ${source}`);
    assert.equal(row.targetModule, 'main', `wrong target module for ${source}`);
    assert.equal(row.nav.group, 'Reference', `wrong nav group for ${source}`);

    const navTarget = expectedNav.get(contract.id);
    const navPattern = new RegExp(`^\\* xref:${navTarget}\\.adoc\\[[^\\]]+\\]$`, 'm');
    assert.match(nav, navPattern, `missing mapped nav entry: ${contract.id}`);
    assert.equal([...nav.matchAll(new RegExp(`xref:${navTarget}\\.adoc\\[`, 'g'))].length, 1, `duplicate nav entry: ${contract.id}`);

    const pagePath = targetPagePath(options.pagesPath, row.targetPageId);
    assert.ok(existsSync(pagePath), `missing target page: ${contract.id}`);
    const page = readFileSync(pagePath, 'utf8');
    const sourcePath = resolve(sourceRoot, source.slice('docs/content/docs/'.length));
    assert.ok(sourcePath.startsWith(`${resolve(sourceRoot)}/`), `source path escapes source root: ${source}`);
    const sourceText = readFileSync(sourcePath, 'utf8');
    assert.equal(createHash('sha256').update(sourceText).digest('hex'), row.sha256, `source hash differs from frozen manifest: ${source}`);
    assert.match(page, /^= .+$/m, `missing page title: ${contract.id}`);
    for (const heading of contract.headings) {
      assert.match(page, new RegExp(`^={2,3} ${heading.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`, 'm'), `missing topic heading "${heading}" in ${contract.id}`);
    }
    const codeBlockCount = [...page.matchAll(/^\[source(?:,[^\]]+)?\]\n----$/gm)].length;
    assert.ok(codeBlockCount >= contract.code, `${contract.id} has ${codeBlockCount} code blocks; expected at least ${contract.code}`);
    const tableCount = [...page.matchAll(/^\|===$/gm)].length / 2;
    assert.ok(tableCount >= contract.tables, `${contract.id} has ${tableCount} tables; expected at least ${contract.tables}`);
    const uncommentedPage = page.replace(/^\/\/.*$/gm, '');
    assert.ok(!uncommentedPage.includes('.mdx'), `unconverted MDX link in ${contract.id}`);
    const parity = assertSourceParity(sourceText, page, source, contract.id);

    const xrefs = [...page.matchAll(/\bxref:([^\s\[]+)\[[^\]]*\]/g)].map(([, reference]) => reference);
    for (const reference of xrefs) {
      assert.ok(!reference.startsWith('../') && !reference.includes('/../'), `filesystem-relative xref in ${contract.id}: ${reference}`);
      const [module, target] = reference.includes(':') ? reference.split(':', 2) : ['main', reference];
      assert.ok(target.endsWith('.adoc'), `xref must target an AsciiDoc page in ${contract.id}: ${reference}`);
      const targetId = `${module}:${target.slice(0, -5)}`;
      assert.match(targetId, /^[a-z][a-z0-9-]*:[a-z0-9/-]+$/, `invalid xref page ID in ${contract.id}: ${targetId}`);
      assert.ok(allowedTargets.has(targetId), `xref target is absent from manifest in ${contract.id}: ${targetId}`);
      assert.ok(declaredModules.has(module), `xref module is not registered in ${contract.id}: ${module}`);
      if (!options.allowPendingTargets) {
        const targetPagesDir = resolve(options.pagesPath, '..', '..', module, 'pages');
        assert.ok(existsSync(targetPagePath(targetPagesDir, targetId)), `missing xref target ${targetId} from ${contract.id}`);
      }
    }

    results.push({ source, targetPageId: contract.id, codeBlocks: codeBlockCount, sourceCodeBlocks: parity.sourceCodeCount, tables: tableCount, sourceTableRows: parity.sourceTableRows, headings: parity.sourceParts.headings.length + 1, xrefs: xrefs.length });
  }

  const diagramPath = join(options.pagesPath, 'components/preprocessors/speculative-decoding.adoc');
  const diagram = readFileSync(diagramPath, 'utf8');
  assert.match(diagram, /^\[mermaid\]\n----\naccTitle: .+\naccDescr: .+\nflowchart LR$/m, 'speculative-decoding Mermaid source must include accessible title and description');
  const sourceDiagram = results.find(({ source }) => source.endsWith('/speculative-decoding.mdx'));
  assert.equal(sourceDiagram && parseSource(readFileSync(join(sourceRoot, 'components/preprocessors/speculative-decoding.mdx'), 'utf8')).codeBlocks.filter(({ language }) => language === 'mermaid').length, 1, 'speculative-decoding source must contain one diagram');
  assert.match(diagram, /xref:components\/preprocessors\/whitespace-normalization\.adoc\[/, 'speculative-decoding page must link to mapped whitespace page');
  assert.match(readFileSync(join(options.pagesPath, 'components/preprocessors/whitespace-normalization.adoc'), 'utf8'), /xref:components\/preprocessors\/speculative-decoding\.adoc\[/, 'whitespace page must link to mapped speculative-decoding page');

  console.log(JSON.stringify({
    result: 'CONTENT_CHECK_OK',
    group: 'loaders-preprocessors',
    sourceCount: results.length,
    pendingTargetsAllowed: options.allowPendingTargets,
    pages: results,
  }, null, 2));
}

try {
  run();
} catch (error) {
  console.error(`CONTENT_CHECK_FAILED: ${error.message}`);
  process.exitCode = 1;
}
