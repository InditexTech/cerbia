#!/usr/bin/env node

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, posix, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const defaultManifest = join(repoRoot, 'docs/scripts/migration/legacy-routes.json');
const defaultContentRoot = join(repoRoot, 'docs/src');
const defaultSourceRoot = join(repoRoot, 'docs/content/docs/components');
const asciidoctor = createRequire(join(repoRoot, 'docs/package.json'))('@asciidoctor/core')();

const expected = {
  scanners: {
    directory: 'scanners',
    pages: ['index', 'canary-leak', 'invisible-text', 'keyword', 'pii', 'pii-presidio', 'prompt-injection', 'prompt-injection-protectai', 'secrets', 'url-malicious', 'url-allowlist', 'xss'],
    entries: [
      ['canary-leak', 'cerbia.core.scanners.CanaryLeakScanner'],
      ['invisible-text', 'cerbia.core.scanners.InvisibleTextScanner'],
      ['keyword', 'cerbia.core.scanners.KeywordScanner'],
      ['pii', 'cerbia.core.scanners.PiiScanner'],
      ['pii-presidio', 'cerbia.presidio.scanners.PresidioPiiScanner'],
      ['prompt-injection', 'cerbia.core.scanners.PromptInjectionScanner'],
      ['prompt-injection-protectai', 'cerbia.protectai.scanners.ProtectAIPromptInjectionScanner'],
      ['secrets', 'cerbia.core.scanners.SecretScanner'],
      ['url-malicious', 'cerbia.core.scanners.MaliciousUrlScanner'],
      ['url-allowlist', 'cerbia.core.scanners.UrlAllowlistScanner'],
      ['xss', 'cerbia.core.scanners.XssScanner'],
    ],
  },
  aggregators: {
    directory: 'score-aggregators',
    pages: ['index', 'max', 'max-with-bonus', 'mean'],
    entries: [
      ['max', 'cerbia.core.score_aggregators.MaxScoreAggregator'],
      ['max-with-bonus', 'cerbia.core.score_aggregators.MaxWithBonusScoreAggregator'],
      ['mean', 'cerbia.core.score_aggregators.MeanScoreAggregator'],
    ],
  },
};

const scannerModuleByClass = {
  CanaryLeakScanner: 'canary',
  InvisibleTextScanner: 'invisible_text',
  KeywordScanner: 'keyword',
  PiiScanner: 'pii',
  PresidioPiiScanner: 'pii',
  PromptInjectionScanner: 'prompt_injection',
  ProtectAIPromptInjectionScanner: 'prompt_injection',
  SecretScanner: 'secret',
  MaliciousUrlScanner: 'malicious_url',
  UrlAllowlistScanner: 'url_allowlist',
  XssScanner: 'xss',
};

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    assert.ok(argument.startsWith('--'), `unexpected argument: ${argument}`);
    const name = argument.slice(2);
    assert.ok(['content', 'group', 'allow-pending-targets', 'manifest', 'content-root', 'source-root'].includes(name), `unknown option: ${argument}`);
    assert.ok(!Object.hasOwn(options, name), `duplicate option: ${argument}`);
    if (name === 'content' || name === 'allow-pending-targets') {
      options[name] = true;
      continue;
    }
    const value = argv[index + 1];
    assert.ok(value && !value.startsWith('--'), `missing value for ${argument}`);
    options[name] = value;
    index += 1;
  }
  assert.equal(options.content, true, 'required mode: --content');
  assert.equal(options.group, 'scanners-aggregators', 'required group: --group scanners-aggregators');
  options.manifestPath = resolve(options.manifest || defaultManifest);
  options.contentRoot = resolve(options['content-root'] || defaultContentRoot);
  options.sourceRoot = resolve(options['source-root'] || defaultSourceRoot);
  options.allowPendingTargets = options['allow-pending-targets'] === true;
  return options;
}

function read(path, label) {
  assert.ok(existsSync(path), `missing ${label}: ${path}`);
  return readFileSync(path, 'utf8');
}

function normalizedCell(value) {
  return value
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/&(?:amp|#38);/g, '&')
    .replace(/&(?:lt|#60);/g, '<')
    .replace(/&(?:gt|#62);/g, '>')
    .replace(/&(?:quot|#34);/g, '"')
    .replace(/&#(?:39|x27);/gi, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function sourceTables(source) {
  const lines = source.split(/\r?\n/);
  const tables = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (!/^\s*\|.*\|\s*$/.test(lines[index]) || !/^\s*\|\s*:?-{3,}/.test(lines[index + 1] ?? '')) continue;
    const rows = [lines[index]];
    index += 2;
    while (index < lines.length && /^\s*\|.*\|\s*$/.test(lines[index])) {
      rows.push(lines[index]);
      index += 1;
    }
    index -= 1;
    tables.push(rows.map((line) => line.trim().replace(/^\|\s*/, '').replace(/\s*\|$/, '').split(/\s*\|\s*/).map(normalizedCell)));
  }
  return tables;
}

function renderedTables(adoc) {
  const html = asciidoctor.convert(adoc, { safe: 'safe' });
  return [...html.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/gi)].map(([, table]) => {
    return [...table.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)].map(([, row]) => {
      return [...row.matchAll(/<t[hd]\b[^>]*>([\s\S]*?)<\/t[hd]>/gi)]
        .map(([, cell]) => normalizedCell(cell.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ')));
    });
  });
}

function pagePath(contentRoot, pageId) {
  const separator = pageId.indexOf(':');
  assert.ok(separator > 0, `invalid target page ID: ${pageId}`);
  const module = pageId.slice(0, separator);
  const relativePage = pageId.slice(separator + 1);
  assert.match(relativePage, /^[a-z0-9/-]+$/, `invalid target page path: ${pageId}`);
  return join(contentRoot, 'modules', module, 'pages', `${relativePage}.adoc`);
}

function assertSelectorImplementation(selector, sourcePath) {
  const [modulePath, className] = [selector.slice(0, selector.lastIndexOf('.')), selector.slice(selector.lastIndexOf('.') + 1)];
  const sourceText = read(sourcePath, `implementation source for ${selector}`);
  assert.match(sourceText, new RegExp(`^class ${className}\\b`, 'm'), `selector class does not match source definition: ${selector}`);
  const factoryPath = selector.includes('.score_aggregators.')
    ? join(repoRoot, 'packages/cerbia-core/src/cerbia/core/factories/score_aggregator.py')
    : join(repoRoot, 'packages/cerbia-core/src/cerbia/core/factories/scanner.py');
  const factorySource = read(factoryPath, `component factory ${factoryPath}`);
  assert.match(factorySource, /class (?:Scanner|ScoreAggregator)Factory\(/, `factory declaration missing for ${selector}`);
  const factoryBase = read(join(repoRoot, 'packages/cerbia-core/src/cerbia/core/factories/base.py'), 'dynamic component factory implementation');
  assert.match(factoryBase, /importlib\.import_module\(module_path\)/, 'factory must import the configured module path');
  assert.match(factoryBase, /getattr\(module, class_name\)/, 'factory must select the configured class name');

  if (selector.startsWith('cerbia.core.scanners.')) {
    const exports = read(join(repoRoot, 'packages/cerbia-core/src/cerbia/core/scanners/__init__.py'), 'core scanner exports');
    assert.match(exports, new RegExp(`from \.${className === 'CanaryLeakScanner' ? 'canary' : className === 'InvisibleTextScanner' ? 'invisible_text' : className === 'KeywordScanner' ? 'keyword' : className === 'MaliciousUrlScanner' ? 'malicious_url' : className === 'PiiScanner' ? 'pii' : className === 'PromptInjectionScanner' ? 'prompt_injection' : className === 'SecretScanner' ? 'secret' : className === 'UrlAllowlistScanner' ? 'url_allowlist' : 'xss'} import ${className}`), `selector is not exported by cerbia.core.scanners: ${selector}`);
  } else if (selector.startsWith('cerbia.presidio.scanners.')) {
    const exports = read(join(repoRoot, 'packages/cerbia-presidio/src/cerbia/presidio/scanners/__init__.py'), 'Presidio scanner exports');
    assert.match(exports, new RegExp(`from \.pii import ${className}`), `selector is not exported by cerbia.presidio.scanners: ${selector}`);
  } else if (selector.startsWith('cerbia.protectai.scanners.')) {
    const exports = read(join(repoRoot, 'packages/cerbia-protectai/src/cerbia/protectai/scanners/__init__.py'), 'ProtectAI scanner exports');
    assert.match(exports, new RegExp(`from \.prompt_injection import ${className}`), `selector is not exported by cerbia.protectai.scanners: ${selector}`);
  } else if (selector.startsWith('cerbia.core.score_aggregators.')) {
    const exports = read(join(repoRoot, 'packages/cerbia-core/src/cerbia/core/score_aggregators/__init__.py'), 'score aggregator exports');
    assert.match(exports, new RegExp(`from \.${className === 'MaxWithBonusScoreAggregator' ? 'max_with_bonus' : className === 'MaxScoreAggregator' ? 'max' : 'mean'} import ${className}`), `selector is not exported by cerbia.core.score_aggregators: ${selector}`);
  }
  assert.ok(modulePath.length > 0, `empty module path for ${selector}`);
}

function checkGroup(name, group, manifest, options, nav) {
  const metaPath = join(options.sourceRoot, group.directory, 'meta.json');
  const meta = JSON.parse(read(metaPath, `${name} source metadata`));
  assert.equal(meta.title, name === 'scanners' ? 'Scanners' : 'Score aggregators', `${name} metadata title changed`);
  assert.deepEqual(meta.pages, group.pages, `${name} source metadata order changed`);

  const sources = group.pages.map((page) => `docs/content/docs/components/${group.directory}/${page}.mdx`);
  const rows = manifest.routes.filter(({ source }) => sources.includes(source));
  assert.equal(rows.length, group.pages.length, `${name} manifest source count mismatch`);
  assert.deepEqual(new Set(rows.map(({ source }) => source)), new Set(sources), `${name} manifest sources differ from source metadata`);

  const entryByPage = new Map(group.entries);
  const sourceClasses = [];
  let headingCount = 0;
  let snippetCount = 0;
  let sourceTableCount = 0;
  let renderedTableCount = 0;
  let tableRowCount = 0;
  for (const page of group.pages) {
    const sourceRelative = `docs/content/docs/components/${group.directory}/${page}.mdx`;
    const sourcePath = join(repoRoot, sourceRelative);
    const source = read(sourcePath, `MDX source ${sourceRelative}`);
    const row = rows.find(({ source: mapped }) => mapped === sourceRelative);
    const target = row.targetPageId;
    assert.equal(row.targetModule, 'main', `unexpected target module: ${sourceRelative}`);
    assert.equal(target, `main:components/${group.directory}${page === 'index' ? '' : `/${page}`}`, `wrong mapped target: ${sourceRelative}`);
    const targetPath = pagePath(options.contentRoot, target);
    const targetText = read(targetPath, `mapped AsciiDoc target ${target}`);
    const navTarget = `xref:components/${group.directory}${page === 'index' ? '' : `/${page}`}.adoc[`;
    assert.ok(nav.includes(navTarget), `target absent from main nav: ${target}`);

    const expectedTables = sourceTables(source);
    const actualTables = renderedTables(targetText);
    assert.equal(actualTables.length, expectedTables.length, `rendered table count mismatch in ${target}: source=${expectedTables.length}, target=${actualTables.length}`);
    for (let tableIndex = 0; tableIndex < expectedTables.length; tableIndex += 1) {
      const expectedRows = expectedTables[tableIndex];
      const actualRows = actualTables[tableIndex];
      for (const expectedRow of expectedRows) {
        const matchingRow = actualRows.find((actualRow) => expectedRow.length === actualRow.length && expectedRow.every((cell, cellIndex) => cell === actualRow[cellIndex]));
        assert.ok(matchingRow, `source table row missing or changed in ${target}: ${expectedRow.join(' | ')}`);
        tableRowCount += 1;
      }
    }
    sourceTableCount += expectedTables.length;
    renderedTableCount += actualTables.length;

    const sourceTitle = source.match(/^title:\s*["']?([^"'\n]+)["']?\s*$/m)?.[1];
    assert.ok(sourceTitle, `missing source title: ${sourceRelative}`);
    const heading = targetText.match(/^= (.+)$/m)?.[1];
    assert.ok(heading && heading.toLowerCase() === sourceTitle.toLowerCase(), `heading coverage mismatch for ${sourceRelative}: expected ${sourceTitle}, found ${heading}`);
    headingCount += 1;

    const prose = source.replace(/^---[\s\S]*?---\s*/m, '').trim();
    const sourceWords = prose.match(/[A-Za-z0-9][A-Za-z0-9'-]*/g)?.length ?? 0;
    const targetWords = targetText.replace(/^:[\w-]+:.*$/gm, ' ').replace(/^={1,6}\s+.*$/gm, ' ').match(/[A-Za-z0-9][A-Za-z0-9'-]*/g)?.length ?? 0;
    assert.ok(targetWords >= Math.floor(sourceWords * 0.88), `content appears truncated for ${sourceRelative}: source=${sourceWords}, target=${targetWords}`);

    const sourceFences = [...source.matchAll(/```(\w+)?\n([\s\S]*?)\n```/g)];
    const targetFences = [...targetText.matchAll(/^\[source(?:,([^\]]+))?\]\n----\n([\s\S]*?)\n----$/gm)];
    assert.equal(targetFences.length, sourceFences.length, `code example count mismatch for ${sourceRelative}`);
    for (const [, sourceLanguage, sourceCode] of sourceFences) {
      const normalizedCode = sourceCode.replaceAll('\r\n', '\n').trim();
      assert.ok(targetText.includes(normalizedCode), `code example changed or missing in ${sourceRelative}`);
      if (sourceLanguage === 'yaml') assert.match(targetText, /\[source,yaml\]/, `YAML source block missing for ${sourceRelative}`);
      snippetCount += 1;
    }

    const sourcePagePath = sourceRelative.slice('docs/content/docs/'.length);
    for (const [, sourceHref] of source.matchAll(/\]\(([^)#]+\.mdx)(?:#[^)]*)?\)/g)) {
      const linkedSource = `docs/content/docs/${posix.normalize(posix.join(posix.dirname(sourcePagePath), sourceHref))}`;
      const linkedRow = manifest.routes.find(({ source: candidate }) => candidate === linkedSource);
      assert.ok(linkedRow, `source link does not map to a manifest page: ${sourceRelative} -> ${sourceHref}`);
      const linkedTarget = linkedRow.targetModule === 'main'
        ? linkedRow.targetPageId.slice('main:'.length)
        : `${linkedRow.targetModule}:${linkedRow.targetPageId.slice(`${linkedRow.targetModule}:`.length)}`;
      const href = `xref:${linkedTarget}.adoc[`;
      assert.ok(targetText.includes(href), `source cross-reference not converted for ${sourceRelative}: ${sourceHref}`);
    }

    const mappedIds = new Set([
      ...manifest.routes.map(({ targetPageId }) => targetPageId),
      ...(manifest.navigation?.mainSections ?? []).map(({ entryPageId }) => entryPageId),
    ]);
    for (const [, reference] of targetText.matchAll(/\bxref:([^\s\[]+)\[[^\]]*\]/g)) {
      const resource = reference.replace(/#.*$/, '').replace(/\.adoc$/, '');
      const separator = resource.indexOf(':');
      const targetModule = separator === -1 ? 'main' : resource.slice(0, separator);
      const targetPage = separator === -1 ? resource : resource.slice(separator + 1);
      const referenceId = `${targetModule}:${targetPage}`;
      assert.ok(mappedIds.has(referenceId), `xref is not represented by the migration map: ${target} -> ${referenceId}`);
      if (!options.allowPendingTargets) {
        assert.ok(existsSync(pagePath(options.contentRoot, referenceId)), `missing xref target ${referenceId} from ${target}`);
      }
    }

    const selector = entryByPage.get(page);
    if (selector) {
      const selectorKey = name === 'scanners' ? 'scanner' : 'score_aggregator';
      const documentedSelector = [...targetText.matchAll(new RegExp(`^[ \\t]*(?:-[ \\t]*)?${selectorKey}:[ \\t]*([^ \\t\\r\\n\\]]+)`, 'gm'))]
        .map(([, value]) => value)
        .find((value) => value.startsWith('cerbia.'));
      assert.equal(documentedSelector, selector, `selector mismatch in ${target}`);
      const modulePieces = selector.match(/^((?:cerbia\.)+[a-zA-Z0-9_.]+)\.([A-Z][A-Za-z0-9_]*)$/);
      assert.ok(modulePieces, `invalid qualified selector in ${target}: ${selector}`);
      const actualModuleSource = selector.includes('.score_aggregators.')
        ? join(repoRoot, 'packages/cerbia-core/src/cerbia/core/score_aggregators', `${page.replaceAll('-', '_')}.py`)
        : modulePieces[2] === 'PresidioPiiScanner'
          ? join(repoRoot, 'packages/cerbia-presidio/src/cerbia/presidio/scanners/pii.py')
          : join(
            repoRoot,
            'packages',
            selector.startsWith('cerbia.core.') ? 'cerbia-core' : 'cerbia-protectai',
            'src',
            'cerbia',
            ...modulePieces[1].replace(/^cerbia\./, '').split('.'),
            scannerModuleByClass[modulePieces[2]],
            '_scanner.py',
          );
      const classSource = read(actualModuleSource, `selector implementation ${selector}`);
      assert.match(classSource, new RegExp(`^class ${modulePieces[2]}\\b`, 'm'), `selector class not defined in implementation: ${selector}`);
      assertSelectorImplementation(selector, actualModuleSource);
      sourceClasses.push({ page, selector, implementation: actualModuleSource.slice(repoRoot.length + 1) });
    }
  }

  return { name, sourceCount: sources.length, targetCount: rows.length, headingCoverage: headingCount, snippetCoverage: snippetCount, sourceTables: sourceTableCount, renderedTables: renderedTableCount, tableRows: tableRowCount, sourceClasses };
}

try {
  const options = parseArgs(process.argv.slice(2));
  const manifest = JSON.parse(read(options.manifestPath, 'legacy route manifest'));
  const nav = read(join(options.contentRoot, 'modules/main/nav.adoc'), 'main module navigation');
  const protectedPages = new Set([
    ...manifest.routes.filter(({ source }) => source.includes('/components/scanners/') || source.includes('/components/score-aggregators/')).map(({ targetPageId }) => targetPageId),
  ]);
  assert.equal(protectedPages.size, 16, 'expected exactly 16 unique scanner and aggregator target IDs');

  const scannerResult = checkGroup('scanners', expected.scanners, manifest, options, nav);
  const aggregatorResult = checkGroup('aggregators', expected.aggregators, manifest, options, nav);
  const pending = options.allowPendingTargets;
  const mappedRoutes = [...expected.scanners.pages.map((page) => ['scanners', page]), ...expected.aggregators.pages.map((page) => ['score-aggregators', page])];
  const expectedNavTargets = mappedRoutes.map(([directory, page]) => `xref:components/${directory}${page === 'index' ? '' : `/${page}`}.adoc[`);
  const actualNavTargets = [...nav.matchAll(/^\* xref:(components\/(?:scanners|score-aggregators)(?:\/[a-z0-9-]+)?)\.adoc\[/gm)].map(([, path]) => `xref:${path}.adoc[`);
  assert.deepEqual(actualNavTargets, expectedNavTargets, 'scanner and score-aggregator nav targets are missing, duplicated, or out of source metadata order');
  const absent = mappedRoutes.filter(([directory, page]) => !existsSync(pagePath(options.contentRoot, `main:components/${directory}${page === 'index' ? '' : `/${page}`}`)));
  if (!pending) assert.equal(absent.length, 0, `missing indexed content targets: ${absent.map(([, page]) => page).join(', ')}`);
  console.log(JSON.stringify({ status: 'CONTENT_SCANNERS_AGGREGATORS_OK', allowPendingTargets: pending, mappedTargetCount: protectedPages.size, missingTargets: absent.map(([directory, page]) => `main:components/${directory}${page === 'index' ? '' : `/${page}`}`), navOrder: expected.scanners.pages.slice(1).concat(expected.aggregators.pages.slice(1)), groups: [scannerResult, aggregatorResult] }, null, 2));
} catch (error) {
  console.error(`CONTENT_SCANNERS_AGGREGATORS_FAILED: ${error.message}`);
  process.exitCode = 1;
}
