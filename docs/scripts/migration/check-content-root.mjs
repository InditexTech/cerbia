import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const args = process.argv.slice(2);

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function normalizeWords(value) {
  return value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replaceAll('_', ' ')
    .toLowerCase()
    .match(/[\p{L}\p{N}]+/gu) ?? [];
}

function stripMarkup(value) {
  return value
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/xref:[^\[]+\[([^\]]*)\]/g, '$1')
    .replace(/link:[^\[]+\[([^\]]*)\]/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[*_]{1,2}([^*_]+)[*_]{1,2}/g, '$1')
    .replace(/&gt;/g, '>')
    .replace(/&lt;/g, '<')
    .replace(/&amp;/g, '&');
}

function tableCell(value) {
  return stripMarkup(value.trim()).toLowerCase();
}

function extractSource(source) {
  const frontmatter = source.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/)?.[1] ?? '';
  const title = frontmatter.match(/^title:\s*["']?(.*?)["']?\s*$/m)?.[1] ?? '';
  const body = source.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  const proseBody = body.replace(/^```[\w+-]*\s*\r?\n[\s\S]*?^```\s*$/gm, '');
  const headings = [...proseBody.matchAll(/^#{1,6}\s+(.+?)\s*#*\s*$/gm)].map(([, heading]) => stripMarkup(heading).trim());
  const codeBlocks = [...body.matchAll(/^```([\w+-]*)\s*\r?\n([\s\S]*?)^```\s*$/gm)].map(([, language, code]) => ({
    language: language.toLowerCase(),
    code: code.trimEnd(),
  }));
  const tableRows = proseBody.split(/\r?\n/).filter((line) => /^\s*\|/.test(line) && !/^\s*\|\s*:?-{3,}/.test(line));
  const prose = body
    .replace(/^```[\w+-]*\s*\r?\n[\s\S]*?^```\s*$/gm, '')
    .replace(/^#{1,6}\s+.+$/gm, '')
    .replace(/^\s*\|.*$/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/<[^>]+>/g, ' ');
  return { title, headings, codeBlocks, tableRows, prose };
}

function extractTarget(target) {
  const headings = [...target.matchAll(/^(={1,6})\s+(.+?)\s*$/gm)].map(([, , heading]) => stripMarkup(heading).trim());
  const codeBlocks = [...target.matchAll(/^\[source,([^\]]+)\]\s*\r?\n-{4,}\r?\n([\s\S]*?)\r?\n-{4,}\s*$/gm)].map(([, language, code]) => ({
    language: language.split(',')[0].toLowerCase(),
    code: code.trimEnd(),
  }));
  const tableRows = [...target.matchAll(/^\|===\s*\r?\n([\s\S]*?)^\|===\s*$/gm)].flatMap(([, table]) =>
    table.split(/\r?\n/).filter((line) => line.startsWith('|')).map((line) => `| ${line.slice(1).trim()}`));
  const mermaidBlocks = [...target.matchAll(/^\[mermaid\]\s*\r?\n-{4,}\r?\n([\s\S]*?)\r?\n-{4,}\s*$/gm)].map(([, diagram]) =>
    diagram.split(/\r?\n/).filter((line) => !/^\s*acc(?:Title|Descr)\s*:/i.test(line)).join('\n').trimEnd());
  const prose = target
    .replace(/^\|===\s*\r?\n[\s\S]*?^\|===\s*$/gm, '')
    .replace(/^\/\/.*$/gm, '')
    .replace(/^={1,6}\s+.+$/gm, '')
    .replace(/^\[source,[^\]]+\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\[mermaid\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\|===\s*\r?\n[\s\S]*?^\|===\s*$/gm, '')
    .replace(/^\s*\|.*$/gm, '')
    .replace(/^\s*[*.-]+\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^:.*$/gm, '');
  return { headings, codeBlocks, tableRows, mermaidBlocks, prose };
}

function assertWordCoverage(sourceText, targetText, sourcePath) {
  const targetNarrative = targetText
    .replace(/^\[source,[^\]]+\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\[mermaid\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\|===\s*\r?\n[\s\S]*?^\|===\s*$/gm, '');
  const targetWords = new Set(normalizeWords(stripMarkup(targetNarrative)));
  for (const word of new Set(normalizeWords(stripMarkup(sourceText)))) {
    assert.ok(targetWords.has(word), `source prose token missing from target ${sourcePath}: ${word}`);
  }
}

function proseParagraphs(text, source) {
  let prose = text;
  if (source) prose = prose.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
  prose = prose
    .replace(/^```[\w+-]*\s*\r?\n[\s\S]*?^```\s*$/gm, '')
    .replace(/^\[source,[^\]]+\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\[mermaid\]\s*\r?\n-{4,}\r?\n[\s\S]*?\r?\n-{4,}\s*$/gm, '')
    .replace(/^\|===\s*\r?\n[\s\S]*?^\|===\s*$/gm, '')
    .replace(/^\|.*$/gm, '')
    .replace(/^#{1,6}\s+.+$/gm, '')
    .replace(/^={1,6}\s+.+$/gm, '')
    .replace(/^\/\/.*$/gm, '')
    .replace(/^:.*$/gm, '');
  return prose.split(/\r?\n\s*\r?\n/).map((paragraph) => paragraph.trim()).filter(Boolean);
}

function normalizeParagraph(paragraph) {
  return normalizeWords(stripMarkup(paragraph));
}

function assertSourceParagraph(sourceText, targetText, sourcePath, anchor) {
  const sourceParagraph = proseParagraphs(sourceText, true).find((paragraph) => paragraph.toLowerCase().includes(anchor.toLowerCase()));
  assert.ok(sourceParagraph, `source paragraph anchor not found in ${sourcePath}: ${anchor}`);
  const expected = normalizeParagraph(sourceParagraph);
  const targetParagraphs = proseParagraphs(targetText, false).map(normalizeParagraph);
  assert.ok(targetParagraphs.some((paragraph) =>
    paragraph.length === expected.length && paragraph.every((word, index) => word === expected[index])),
  `source prose paragraph changed in ${sourcePath}: ${anchor}`);
}

try {
  if (args.includes('--self-test')) {
    assert.deepEqual(args, ['--self-test'], 'usage: check-content-root.mjs --self-test');
    const manifest = JSON.parse(readFileSync(join(repoRoot, 'docs/scripts/migration/legacy-routes.json'), 'utf8'));
    const sourceNames = ['index.mdx', 'architecture.mdx', 'getting-started.mdx', 'configuration.mdx', 'cli.mdx', 'gate.mdx', 'i18n.mdx', 'logging.mdx'];
    const rows = manifest.routes.filter(({ source }) => sourceNames.includes(source.slice('docs/content/docs/'.length)));
    const fixtures = [
      {
        name: 'heading',
        sourcePage: 'architecture',
        find: '== Pipeline overview',
        replace: '== Omitted heading',
        expected: /missing source heading/,
      },
      {
        name: 'code',
        sourcePage: 'cli',
        find: 'cerbia validate examples/cli-usage/config.cerbia.yaml',
        replace: 'cerbia validate OMITTED.yaml',
        expected: /missing or changed bash code block/,
      },
      {
        name: 'truncated-i18n-paragraph',
        sourcePage: 'i18n',
        find: 'the selected language packs.',
        replace: '',
        expected: /source prose paragraph changed.*receive patterns from/,
      },
      {
        name: 'duplicated-cli-paragraph',
        sourcePage: 'cli',
        find: 'metadata, `aggregated_score`, rationale',
        replace: 'metadata, `aggregated_score`, the aggregated score, rationale',
        expected: /source prose paragraph changed.*Every entry result includes/,
      },
    ];
    for (const fixture of fixtures) {
      const pagesDir = mkdtempSync(join(tmpdir(), `cerbia-content-root-${fixture.name}-`));
      try {
        for (const row of rows) {
          const target = row.targetPageId.slice('main:'.length);
          cpSync(join(repoRoot, 'docs/src/modules/main/pages', `${target}.adoc`), join(pagesDir, `${target}.adoc`));
        }
        const path = join(pagesDir, `${fixture.sourcePage}.adoc`);
        const contents = readFileSync(path, 'utf8');
        assert.ok(contents.includes(fixture.find), `fixture anchor missing: ${fixture.name}`);
        writeFileSync(path, contents.replace(fixture.find, fixture.replace));
        const result = spawnSync(process.execPath, [
          fileURLToPath(import.meta.url),
          '--content', '--group', 'root', '--allow-pending-targets', '--pages-dir', pagesDir,
        ], { encoding: 'utf8' });
        assert.equal(result.status, 1, `${fixture.name} omission fixture unexpectedly passed: ${result.stdout}${result.stderr}`);
        assert.match(result.stderr, fixture.expected, `${fixture.name} fixture failed for the wrong reason: ${result.stderr}`);
      } finally {
        rmSync(pagesDir, { recursive: true, force: true });
      }
    }
    console.log(`CONTENT_ROOT_NEGATIVE_OK fixtures=${fixtures.map(({ name }) => name).join(',')} cleanup=true`);
    process.exit(0);
  }
  const flags = args.filter((arg) => arg.startsWith('--') && !['--manifest', '--source-root', '--pages-dir'].includes(arg));
  assert.deepEqual(flags, ['--content', '--group', ...(args.includes('--allow-pending-targets') ? ['--allow-pending-targets'] : [])],
    'usage: check-content-root.mjs --content --group root [--allow-pending-targets] [--manifest FILE] [--source-root DIR] [--pages-dir DIR]');
  assert.equal(args[args.indexOf('--group') + 1], 'root', 'only the root content group is supported');
  const manifestPath = option('--manifest', join(repoRoot, 'docs/scripts/migration/legacy-routes.json'));
  const sourceRoot = option('--source-root', join(repoRoot, 'docs/content/docs'));
  const pagesDir = option('--pages-dir', join(repoRoot, 'docs/src/modules/main/pages'));
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const mappedPageIds = new Set(manifest.routes.map(({ targetPageId }) => targetPageId));
  for (const { entryPageId } of manifest.navigation.mainSections) mappedPageIds.add(entryPageId);
  const expectedSources = [
    'docs/content/docs/index.mdx',
    'docs/content/docs/architecture.mdx',
    'docs/content/docs/getting-started.mdx',
    'docs/content/docs/configuration.mdx',
    'docs/content/docs/cli.mdx',
    'docs/content/docs/gate.mdx',
    'docs/content/docs/i18n.mdx',
    'docs/content/docs/logging.mdx',
  ];
  const rows = manifest.routes.filter(({ source }) => expectedSources.includes(source));
  assert.equal(rows.length, expectedSources.length, 'root source mapping count changed');
  assert.deepEqual(rows.map(({ source }) => source).sort(), [...expectedSources].sort(), 'root source mapping changed');
  assert.equal(new Set(rows.map(({ targetPageId }) => targetPageId)).size, expectedSources.length, 'duplicate root target');

  let headingCount = 0;
  let codeCount = 0;
  let tableCount = 0;
  let diagramCount = 0;
  for (const row of rows) {
    assert.equal(row.targetModule, 'main', `wrong target module for ${row.source}`);
    assert.equal(row.redirectTarget, row.targetPageId, `stale target mapping for ${row.source}`);
    const relativeSource = row.source.slice('docs/content/docs/'.length);
    const sourcePath = join(sourceRoot, relativeSource);
    assert.ok(existsSync(sourcePath), `missing source: ${row.source}`);
    const sourceText = readFileSync(sourcePath, 'utf8');
    assert.equal(createHash('sha256').update(sourceText).digest('hex'), row.sha256, `source changed from frozen baseline: ${row.source}`);
    const page = row.targetPageId.slice('main:'.length);
    const targetPath = join(pagesDir, `${page}.adoc`);
    assert.ok(existsSync(targetPath), `missing target page: ${row.targetPageId} (${targetPath})`);
    const targetText = readFileSync(targetPath, 'utf8');
    for (const [, target] of targetText.matchAll(/xref:([^\[]+)\[[^\]]*\]/g)) {
      const [module, page] = target.includes(':') ? target.split(':', 2) : ['main', target];
      const pageId = `${module}:${page.replace(/\.adoc(?:#.*)?$/, '')}`;
      assert.ok(mappedPageIds.has(pageId), `xref does not target a mapped page: ${row.targetPageId} → ${pageId}`);
    }
    const source = extractSource(sourceText);
    const target = extractTarget(targetText);
    const targetHeadings = new Set(target.headings.map((heading) => heading.toLowerCase()));
    const expectedHeadings = [...source.headings];
    if (source.title && page !== 'about') expectedHeadings.unshift(source.title);
    for (const heading of expectedHeadings) {
      assert.ok(targetHeadings.has(heading.toLowerCase()), `missing source heading in ${row.targetPageId}: ${heading}`);
      headingCount += 1;
    }
    assert.ok(targetText.includes(`Source: ${row.source}`), `missing source traceability comment in ${row.targetPageId}`);

    for (const block of source.codeBlocks.filter(({ language }) => language !== 'mermaid')) {
      const matching = target.codeBlocks.some((candidate) => candidate.language === block.language && candidate.code === block.code);
      assert.ok(matching, `missing or changed ${block.language || 'text'} code block from ${row.source} in ${row.targetPageId}`);
      codeCount += 1;
    }
    for (const rowText of source.tableRows) {
      const cells = rowText.split('|').map(tableCell).filter(Boolean);
      const targetHasRow = target.tableRows.some((candidate) => {
        const targetCells = candidate.split('|').map(tableCell).filter(Boolean);
        return cells.length === targetCells.length && cells.every((cell, index) => cell === targetCells[index]);
      });
      assert.ok(targetHasRow, `missing source table row from ${row.source}: ${rowText}`);
      tableCount += 1;
    }
    if (row.source === 'docs/content/docs/i18n.mdx') {
      assertSourceParagraph(sourceText, targetText, row.source, 'receive patterns from');
    } else if (row.source === 'docs/content/docs/cli.mdx') {
      assertSourceParagraph(sourceText, targetText, row.source, 'Every entry result includes');
    } else {
      assertWordCoverage(`${source.title}\n${source.headings.join('\n')}\n${source.prose}`, targetText, row.source);
    }

    const sourceDiagrams = source.codeBlocks.filter(({ language }) => language === 'mermaid');
    const targetDiagrams = target.mermaidBlocks;
    assert.equal(targetDiagrams.length, sourceDiagrams.length, `Mermaid diagram count changed for ${row.source}`);
    for (const [index, diagram] of sourceDiagrams.entries()) {
      assert.equal(targetDiagrams[index], diagram.code, `Mermaid source changed for ${row.source} diagram ${index + 1}`);
      const mermaidTarget = targetText.matchAll(/^\[mermaid\]\s*\r?\n-{4,}\r?\n([\s\S]*?)\r?\n-{4,}\s*$/gm);
      const blocks = [...mermaidTarget].map(([, contents]) => contents);
      const title = blocks[index].match(/^\s*accTitle:\s*(.+)$/im)?.[1].trim();
      const description = blocks[index].match(/^\s*accDescr:\s*(.+)$/im)?.[1].trim();
      assert.ok(title && title.length >= 4, `missing meaningful Mermaid accTitle in ${row.targetPageId} diagram ${index + 1}`);
      assert.ok(description && description.length >= 12, `missing meaningful Mermaid accDescr in ${row.targetPageId} diagram ${index + 1}`);
      diagramCount += 1;
    }
  }
  assert.equal(diagramCount, 5, 'expected five root Mermaid diagrams');
  console.log(`CONTENT_ROOT_OK pages=${rows.length} headings=${headingCount} codeBlocks=${codeCount} tableRows=${tableCount} mermaid=${diagramCount}`);
} catch (error) {
  console.error(`CONTENT_ROOT_FAILED: ${error.message}`);
  process.exitCode = 1;
}
