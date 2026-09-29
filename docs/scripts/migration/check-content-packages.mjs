import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { frozenSource as readFrozenSource } from './frozen-source.mjs';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const args = process.argv.slice(2);
const packageModules = [
  'cerbia',
  'cerbia-core',
  'cerbia-cli',
  'cerbia-ml',
  'cerbia-presidio',
  'cerbia-protectai',
];
const packageRows = [
  { source: 'docs/content/docs/packages/index.mdx', targetPageId: 'main:packages', targetModule: 'main' },
  ...packageModules.map((module) => ({
    source: `docs/content/docs/packages/${module}.mdx`,
    targetPageId: `${module}:index`,
    targetModule: module,
  })),
];
const requiredContent = new Map([
  ['cerbia', [
    'pip install "cerbia[cli]"',
    'pip install "cerbia[ml]"',
    'pip install "cerbia[presidio]"',
    'pip install "cerbia[protectai]"',
    'pip install "cerbia[all]"',
    'does not provide a Python import namespace',
    'cerbia.core',
    'cerbia.cli',
    'cerbia.ml',
    'cerbia.presidio',
    'cerbia.protectai',
  ]],
  ['cerbia-core', [
    'pip install cerbia-core',
    'cerbia.core',
    'CerbIAConfig',
    'LoaderConfig',
    'ScannerConfig',
    'ScoreAggregatorConfig',
    'from cerbia.core.runner import Runner',
    'Runner(config).scan()',
    'at least one loader and scanner',
    'does not require',
  ]],
  ['cerbia-cli', [
    'pip install cerbia-cli',
    'cerbia validate config.yaml',
    'cerbia scan --config config.yaml --text',
    'status `0`',
    'status `1`',
    'status `2`',
    'log-level',
    'log-file',
  ]],
  ['cerbia-ml', [
    'pip install cerbia-ml',
    'ArtifactCoords',
    '40-character revision',
    'ArtifactSource',
    'HuggingFaceHubSource',
    'is_available',
    'fetch',
    'HuggingFaceClassifierAdapter',
    'ONNX sequence classification model',
    '`local_files_only`',
    'runtime downloads',
  ]],
  ['cerbia-presidio', [
    'pip install cerbia-presidio',
    'cerbia.presidio.scanners.PresidioPiiScanner',
    '`en_core_web_sm`',
    'every supported entity',
    'highest Presidio',
    'match spans',
    'by default',
    'initializes the model',
    'from cerbia.presidio.scanners import PresidioPiiScanner',
  ]],
  ['cerbia-protectai', [
    'pip install cerbia-protectai',
    'pip install "cerbia[protectai]"',
    'cerbia.protectai.scanners.ProtectAIPromptInjectionScanner',
    '`cerbia-ml`',
    '`local_files_only` is `true`',
    '`match_type: full`',
    '`match_type: chunks`',
    '`chunk_size: 256`',
    '`chunk_overlap: 25`',
    'highest injection score',
    'from cerbia.protectai.scanners import ProtectAIPromptInjectionScanner',
  ]],
]);

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${name} value`);
  return resolve(args[index + 1]);
}

function frozenSource(row, sourceRoot) {
  return readFrozenSource(repoRoot, row, sourceRoot);
}

try {
  if (args.includes('--self-test')) {
    assert.deepEqual(args, ['--self-test'], 'usage: check-content-packages.mjs --self-test');
    const fixtures = [
      { name: 'gateway-title', module: 'main', page: 'packages', find: '= Packages', replace: '= Wrong packages', expected: /package gateway title differs/ },
      { name: 'core-pipeline-order', module: 'cerbia-core', page: 'index', find: 'preprocessors in order, then evaluates each resulting entry through the gate.', replace: 'preprocessors independently.', expected: /core pipeline order and scanner behavior/ },
    ];
    for (const fixture of fixtures) {
      const root = mkdtempSync(join(tmpdir(), `cerbia-package-${fixture.name}-`));
      try {
        for (const module of ['main', ...packageModules]) {
          const sourceDir = join(repoRoot, 'docs/src/modules', module);
          const targetDir = join(root, 'modules', module);
          mkdirSync(join(targetDir, 'pages'), { recursive: true });
          cpSync(join(sourceDir, 'nav.adoc'), join(targetDir, 'nav.adoc'));
          const page = module === 'main' ? 'packages' : 'index';
          cpSync(join(sourceDir, 'pages', `${page}.adoc`), join(targetDir, 'pages', `${page}.adoc`));
        }
        const path = join(root, 'modules', fixture.module, 'pages', `${fixture.page}.adoc`);
        const contents = readFileSync(path, 'utf8');
        assert.ok(contents.includes(fixture.find), `fixture anchor missing: ${fixture.name}`);
        writeFileSync(path, contents.replace(fixture.find, fixture.replace));
        const result = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--content', '--group', 'packages', '--allow-pending-targets', '--content-root', root], { encoding: 'utf8' });
        assert.equal(result.status, 1, `${fixture.name} unexpectedly passed: ${result.stdout}${result.stderr}`);
        assert.match(result.stderr, fixture.expected, `${fixture.name} failed for the wrong reason`);
      } finally {
        rmSync(root, { recursive: true, force: true });
      }
    }
    console.log('PACKAGE_CONTENT_NEGATIVE_OK fixtures=gateway-title,core-pipeline-order cleanup=true');
    process.exit(0);
  }
  assert.ok(args.includes('--content'), 'required mode: --content');
  assert.ok(args.includes('--group') && args[args.indexOf('--group') + 1] === 'packages', 'required group: packages');
  const allowedFlags = ['--content', '--group', 'packages', '--allow-pending-targets'];
  const valueOptions = ['--manifest', '--content-root', '--source-root'];
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (valueOptions.includes(arg)) {
      assert.ok(args[index + 1] && !args[index + 1].startsWith('--'), `missing ${arg} value`);
      index += 1;
      continue;
    }
    assert.ok(allowedFlags.includes(arg), `unsupported option: ${arg}`);
  }

  const manifestPath = option('--manifest', join(repoRoot, 'docs/scripts/migration/legacy-routes.json'));
  const contentRoot = option('--content-root', join(repoRoot, 'docs/src'));
  const sourceRoot = option('--source-root', join(repoRoot, 'docs/content/docs'));
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const packageRoutes = manifest.routes.filter(({ source }) => source.startsWith('docs/content/docs/packages/'));
  assert.equal(packageRoutes.length, packageRows.length, 'expected seven frozen package source rows');
  assert.deepEqual(packageRoutes.map(({ source, targetPageId, targetModule }) => ({ source, targetPageId, targetModule }))
    .sort((left, right) => left.source.localeCompare(right.source)),
  [...packageRows].sort((left, right) => left.source.localeCompare(right.source)),
  'package source rows must each map to the gateway or matching package module');

  const mainNav = readFileSync(join(contentRoot, 'modules/main/nav.adoc'), 'utf8');
  assert.equal([...mainNav.matchAll(/^\* xref:packages\.adoc\[Packages\]$/gm)].length, 1,
    'main nav must link the packages gateway exactly once');

  const gatewayPath = join(contentRoot, 'modules/main/pages/packages.adoc');
  assert.ok(existsSync(gatewayPath), 'missing main packages gateway');
  const gateway = readFileSync(gatewayPath, 'utf8');
  const gatewaySource = frozenSource(packageRoutes.find(({ source }) => source.endsWith('/index.mdx')), sourceRoot);
  const gatewaySourceTitle = gatewaySource.match(/^title:\s*["']([^"']+)["']\s*$/m)?.[1];
  const gatewayTitle = gateway.match(/^=\s+(.+)$/m)?.[1];
  assert.ok(gatewaySourceTitle, 'missing package gateway title in source MDX');
  assert.equal(gatewayTitle, gatewaySourceTitle, 'package gateway title differs from source MDX');
  for (const module of packageModules) {
    assert.ok(gatewaySource.includes(`\`${module}\``), `package index source omits distribution: ${module}`);
  }
  const gatewayTargets = [...gateway.matchAll(/\bxref:([a-z][a-z0-9-]*):index\.adoc\[([^\]]+)\]/g)]
    .map(([, module]) => module);
  assert.deepEqual(gatewayTargets, packageModules, 'gateway must link each package module once and in manifest order');
  assert.match(gateway, /xref:prerequisites\.adoc\[/, 'gateway must link product installation requirements');
  assert.match(gateway, /xref:quickstart\.adoc\[/, 'gateway must link the product quickstart');
  assert.doesNotMatch(gateway, /\b(?:ArtifactCoords|HuggingFaceHubSource|PresidioPiiScanner|ProtectAIPromptInjectionScanner|Runner\(|pip install)/,
    'gateway must not duplicate package installation or API details');

  const pendingTargets = args.includes('--allow-pending-targets');
  let pageCount = 0;
  let xrefCount = 0;
  for (const module of packageModules) {
    const pageId = `${module}:index`;
    const pagePath = join(contentRoot, `modules/${module}/pages/index.adoc`);
    const navPath = join(contentRoot, `modules/${module}/nav.adoc`);
    assert.ok(existsSync(pagePath), `missing package module landing: ${pageId}`);
    assert.ok(existsSync(navPath), `missing package module nav: ${module}`);

    const nav = readFileSync(navPath, 'utf8');
    assert.equal([...nav.matchAll(/^\* xref:index\.adoc\[[^\]]+\]$/gm)].length, 1,
      `package module nav must link its index exactly once: ${module}`);
    const source = readFileSync(pagePath, 'utf8');
    const sourcePath = `packages/${module}.mdx`;
    const sourceMdx = frozenSource(packageRoutes.find(({ source: path }) => path === `docs/content/docs/${sourcePath}`), sourceRoot);
    const sourceTitle = sourceMdx.match(/^title:\s*["']([^"']+)["']\s*$/m)?.[1];
    const targetTitle = source.match(/^=\s+(.+)$/m)?.[1];
    assert.ok(sourceTitle, `missing package title in source MDX: ${sourcePath}`);
    assert.equal(targetTitle, sourceTitle, `target title differs from source title: ${sourcePath}`);
    if (module === 'cerbia-core') {
      assert.match(sourceMdx, /requires at least one loader and scanner\. It applies preprocessors in\s+order, then evaluates each resulting entry through the configured scanner set\./,
        'core source pipeline contract changed');
      assert.match(source.replace(/\s+/g, ' '), /requires at least one loader and scanner\. It applies configured preprocessors in order, then evaluates each resulting entry through the gate\./,
        'core pipeline order and scanner behavior missing from target');
    }
    const normalizedSource = source.replace(/\s+/g, ' ');
    assert.match(source, new RegExp(`^= ${module.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\n:description: .+$`, 'm'),
      `missing title or description: ${pageId}`);
    assert.doesNotMatch(source, /full conversion is tracked separately|concise entry point rather than|being converted separately/i,
      `placeholder copy remains: ${pageId}`);
    for (const phrase of requiredContent.get(module)) {
      assert.ok(normalizedSource.includes(phrase), `missing source-grounded package content in ${pageId}: ${phrase}`);
    }
    assert.match(source, /\bxref:main:(?:prerequisites|quickstart|configuration)\.adoc\[/,
      `package landing must link to product-wide setup/reference content: ${pageId}`);

    const xrefs = [...source.matchAll(/\bxref:([^\s\[]+)\[[^\]]*\]/g)].map(([, reference]) => reference);
    for (const reference of xrefs) {
      assert.ok(!reference.startsWith('../') && !reference.includes('/../'), `invalid file-relative xref: ${reference}`);
      const separator = reference.indexOf(':');
      const targetModule = separator === -1 ? module : reference.slice(0, separator);
      const page = (separator === -1 ? reference : reference.slice(separator + 1)).replace(/\.adoc(?:#.*)?$/, '');
      assert.ok(['main', ...packageModules].includes(targetModule), `unknown xref module in ${pageId}: ${reference}`);
      if (!pendingTargets) {
        assert.ok(existsSync(join(contentRoot, `modules/${targetModule}/pages/${page}.adoc`)),
          `missing xref target in ${pageId}: ${reference}`);
      }
      xrefCount += 1;
    }
    pageCount += 1;
  }

  console.log(`PACKAGE_CONTENT_OK sourceRows=${packageRows.length} landings=${pageCount} gatewayTargets=${gatewayTargets.length} xrefs=${xrefCount} pendingTargets=${pendingTargets}`);
} catch (error) {
  console.error(`PACKAGE_CONTENT_FAILED: ${error.message}`);
  process.exitCode = 1;
}
