import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const args = process.argv.slice(2);
const introPages = [
  { id: 'main:about', file: 'about.adoc', requiredTargets: [
    'main:architecture', 'main:prerequisites', 'main:guides-overview', 'main:reference-overview',
  ] },
  { id: 'main:prerequisites', file: 'prerequisites.adoc', requiredTargets: ['main:quickstart'] },
  { id: 'main:guides-overview', file: 'guides-overview.adoc', requiredTargets: [
    'main:quickstart', 'main:configuration', 'main:cli', 'main:components/scanners',
  ] },
  { id: 'main:reference-overview', file: 'reference-overview.adoc', requiredTargets: [
    'main:configuration', 'main:cli', 'main:logging', 'main:i18n', 'main:components/loaders',
    'main:components/preprocessors', 'main:components/scanners', 'main:components/score-aggregators',
    'main:components/custom-components', 'main:packages', 'cerbia:index', 'cerbia-core:index',
    'cerbia-cli:index', 'cerbia-ml:index', 'cerbia-presidio:index', 'cerbia-protectai:index',
  ] },
  { id: 'main:additional-information', file: 'additional-information.adoc', requiredTargets: ['main:reference-overview'] },
  { id: 'main:contributing', file: 'contributing.adoc', requiredTargets: ['main:about'] },
];

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function targetId(reference) {
  assert.ok(!reference.startsWith('../') && !reference.includes('/../'), `relative xref path is not an Antora resource ID: ${reference}`);
  const separator = reference.indexOf(':');
  const module = separator === -1 ? 'main' : reference.slice(0, separator);
  const page = separator === -1 ? reference : reference.slice(separator + 1);
  assert.ok(page.endsWith('.adoc'), `xref must target an AsciiDoc page: ${reference}`);
  const id = `${module}:${page.slice(0, -5)}`;
  assert.match(id, /^[a-z][a-z0-9-]*:[a-z0-9/-]+$/, `invalid Antora resource ID: ${reference}`);
  return id;
}

try {
  const valueOptions = args.filter((arg) => ['--manifest', '--pages-dir'].includes(arg));
  const flags = args.filter((arg) => arg.startsWith('--') && !['--manifest', '--pages-dir'].includes(arg));
  assert.ok(flags.includes('--intros'), 'required mode: --intros');
  assert.ok(flags.every((flag) => flag === '--intros' || flag === '--allow-pending-targets'), 'unsupported option');
  assert.equal(valueOptions.length, new Set(valueOptions).size, 'duplicate path option');

  const manifestPath = option('--manifest', join(repoRoot, 'docs/scripts/migration/legacy-routes.json'));
  const pagesDir = option('--pages-dir', join(repoRoot, 'docs/src/modules/main/pages'));
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const expectedIds = manifest.navigation?.mainSections?.map(({ entryPageId }) => entryPageId);
  assert.deepEqual(expectedIds, introPages.map(({ id }) => id), 'manifest section entry targets changed');

  const allowedTargets = new Set([
    ...expectedIds,
    ...manifest.routes.map(({ targetPageId }) => targetPageId),
  ]);
  const declaredModules = new Set([
    'main',
    ...(manifest.navigation?.packageModules ?? []),
  ]);
  const pendingTargets = args.includes('--allow-pending-targets');
  let xrefCount = 0;

  for (const page of introPages) {
    const path = join(pagesDir, page.file);
    assert.ok(existsSync(path), `missing intro page: ${page.file}`);
    const source = readFileSync(path, 'utf8');
    assert.match(source, new RegExp(`^= .+\\n:description: .+\\n:page-tags: .+\\n:repo-url: https://github\\.com/InditexTech/cerbia$`, 'm'),
      `missing or inconsistent AsciiDoc header in ${page.file}`);
    const uncommentedSource = source.replace(/^\/\/.*$/gm, '');
    assert.match(source, /^:repo-url: https:\/\/github\.com\/InditexTech\/cerbia$/m,
      `missing canonical repository resource in ${page.file}`);
    assert.match(source, /^:example-config-url: \{repo-url\}\/blob\/main\/examples\/cli-usage\/config\.cerbia\.yaml$/m,
      `missing maintained CLI YAML example resource in ${page.file}`);
    assert.ok(!source.includes('../examples/'), `filesystem-relative example link in ${page.file}`);
    const prose = uncommentedSource
      .replace(/^={1,6}\s+.*$/gm, ' ')
      .replace(/^:[\w-]+:.*$/gm, ' ')
      .replace(/^\[.*\]$/gm, ' ')
      .replace(/^[-*|=]+$/gm, ' ')
      .replace(/https?:\/\/\S+/g, ' ')
      .replace(/xref:[^[]+\[[^\]]*\]/g, ' ')
      .replace(/`[^`]*`/g, ' ');
    const wordCount = prose.match(/[A-Za-z0-9][A-Za-z0-9'-]*/g)?.length ?? 0;
    assert.ok(wordCount >= 55, `${page.file} does not contain meaningful authored content (${wordCount} words)`);

    const targets = [...uncommentedSource.matchAll(/\bxref:([^\s\[]+)\[[^\]]*\]/g)]
      .map(([, reference]) => targetId(reference));
    for (const target of targets) {
      assert.ok(allowedTargets.has(target), `unknown manifest xref target in ${page.file}: ${target}`);
      assert.ok(declaredModules.has(target.slice(0, target.indexOf(':'))), `unknown manifest xref module in ${page.file}: ${target}`);
      if (!pendingTargets) {
        const separator = target.indexOf(':');
        const module = target.slice(0, separator);
        const targetPath = join(dirname(dirname(pagesDir)), module, 'pages', `${target.slice(separator + 1)}.adoc`);
        assert.ok(existsSync(targetPath), `missing xref target ${target} from ${page.file}; use --allow-pending-targets only during migration`);
      }
    }
    for (const target of page.requiredTargets) {
      assert.ok(targets.includes(target), `missing intended manifest xref ${target} in ${page.file}`);
    }
    xrefCount += targets.length;
  }

  const prerequisites = readFileSync(join(pagesDir, 'prerequisites.adoc'), 'utf8');
  assert.match(prerequisites, /link:\{example-config-url\}\[CLI example configuration\]/,
    'prerequisites must link to the maintained CLI example configuration');
  for (const page of introPages) {
    const source = readFileSync(join(pagesDir, page.file), 'utf8');
    assert.ok(!source.includes('../examples'), `broken relative examples link in ${page.file}`);
  }

  console.log(`INTROS_OK pages=${introPages.length} xrefs=${xrefCount} pendingTargets=${pendingTargets}`);
} catch (error) {
  console.error(`INTROS_FAILED: ${error.message}`);
  process.exitCode = 1;
}
