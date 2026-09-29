#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const base = 'https://inditextech.github.io/cerbia/';
const defaults = ['README.md', 'examples/README.md', 'examples/cli-usage/README.md',
  'examples/custom-loader/README.md', 'examples/programmatic-usage/README.md',
  ...['cerbia', 'cerbia-core', 'cerbia-cli', 'cerbia-ml', 'cerbia-presidio', 'cerbia-protectai']
    .map((name) => `packages/${name}/README.md`)];

function parse(argv) {
  const options = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    assert.ok(['--content-root', '--inbound', '--example-config', '--logo'].includes(key) && !options.has(key), `invalid or duplicate option: ${key}`);
    assert.ok(argv[index + 1] && !argv[index + 1].startsWith('--'), `missing value for ${key}`);
    options.set(key, resolve(argv[index + 1]));
  }
  return {
    content: options.get('--content-root') ?? join(repo, 'docs/src'),
    inbound: options.get('--inbound') ? [options.get('--inbound')] : defaults.map((path) => join(repo, path)),
    yaml: options.get('--example-config') ?? join(repo, 'examples/cli-usage/config.cerbia.yaml'),
    logo: options.get('--logo') ?? join(repo, 'docs/public/logo.png'),
  };
}

function files(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    assert.ok(!entry.isSymbolicLink(), `symlink in content tree: ${path}`);
    return entry.isDirectory() ? files(path) : entry.isFile() && path.endsWith('.adoc') ? [path] : [];
  });
}

function file(path, label) {
  assert.ok(existsSync(path) && statSync(path).isFile(), `missing ${label}: ${path}`);
  return readFileSync(path, 'utf8');
}

function page(content, module, name, context) {
  assert.match(module, /^[a-z][a-z0-9-]*$/, `invalid module in ${context}`);
  assert.match(name, /^(?:[a-z0-9-]+\/)*[a-z0-9-]+$/, `invalid page in ${context}`);
  file(join(content, 'modules', module, 'pages', `${name}.adoc`), `link target (${context})`);
}

function external(url, content, context) {
  assert.ok(!/[{}]/.test(url), `unresolved URL attribute in ${context}: ${url}`);
  const parsed = new URL(url);
  assert.ok(['http:', 'https:', 'mailto:'].includes(parsed.protocol), `unsupported link scheme: ${url}`);
  if (parsed.protocol === 'mailto:') return;
  assert.ok(parsed.hostname, `missing hostname: ${url}`);
  if (parsed.origin !== new URL(base).origin) return;
  assert.ok(parsed.href.startsWith(base), `site URL outside /cerbia/: ${url}`);
  const parts = parsed.pathname.slice('/cerbia/'.length).split('/').filter(Boolean);
  if (!parts.length) return file(join(content, 'modules/ROOT/pages/index.adoc'), `home (${context})`);
  const version = parts.shift();
  assert.ok(version === 'stable' || version === 'prerelease', `noncanonical documentation URL in ${context}: ${url}`);
  const module = parts.shift() ?? 'ROOT';
  page(content, module, parts.join('/') || 'index', context);
}

try {
  const options = parse(process.argv.slice(2));
  const yaml = file(options.yaml, 'CLI YAML example');
  assert.match(yaml, /(?:loaders|scanners):/, 'CLI YAML example has no gate configuration');
  const logo = file(options.logo, 'logo');
  assert.ok(logo.length > 0, 'empty logo');
  let internal = 0;
  let externalCount = 0;
  for (const path of files(join(options.content, 'modules'))) {
    const rel = relative(join(options.content, 'modules'), path).split(sep);
    const module = rel[0];
    const text = file(path, 'AsciiDoc source');
    const attrs = new Map([...text.matchAll(/^:([a-z][a-z0-9-]*):\s*(.+)$/gm)].map(([, key, value]) => [key, value]));
    function expand(value) {
      for (let attempt = 0; attempt < 4; attempt += 1) {
        if (!/\{[a-z][a-z0-9-]*\}/.test(value)) break;
        value = value.replace(/\{([a-z][a-z0-9-]*)\}/g, (_, key) => {
          assert.ok(attrs.has(key), `undefined URL attribute {${key}}: ${path}`);
          return attrs.get(key);
        });
      }
      return value;
    }
    const prose = text.replace(/^\/\/.*$/gm, '').replace(/^\[source[^\n]*\]\s*\n-{4,}[\s\S]*?\n-{4,}/gm, '');
    for (const [, target] of prose.matchAll(/\bxref:([^\s\[]+)\[[^\]]*\]/g)) {
      const pathId = target.split('#')[0];
      const match = pathId.match(/^(?:([a-z][a-z0-9-]*):)?((?:[a-z0-9-]+\/)*[a-z0-9-]+)\.adoc$/);
      assert.ok(match, `invalid xref in ${path}: ${target}`);
      page(options.content, match[1] ?? module, match[2], path);
      internal += 1;
    }
    for (const [, raw] of prose.matchAll(/\b(?:link:)?(https?:\/\/[^\s\[]+|mailto:[^\s\[]+)\[[^\]]*\]/g)) {
      external(expand(raw), options.content, path);
      externalCount += 1;
    }
    for (const [, raw] of text.matchAll(/^:page-action(?:-secondary)?-url:\s*(\S+)/gm)) {
      if (raw.endsWith('.adoc')) {
        const [targetModule, targetName] = raw.split(':');
        assert.ok(targetName, `invalid page action target: ${raw}`);
        page(options.content, targetModule, targetName.slice(0, -5), path);
        internal += 1;
      } else {
        external(expand(raw), options.content, path);
        externalCount += 1;
      }
    }
  }
  for (const path of options.inbound) {
    const text = file(path, 'inbound README');
    for (const [, url] of text.matchAll(/\]\((https?:\/\/[^)]+)\)/g)) {
      external(url, options.content, path);
      externalCount += 1;
    }
    for (const [, url] of text.matchAll(/\]\((?!https?:\/\/|mailto:|#)([^)]+)\)/g)) {
      assert.ok(!url.includes('..') || resolve(dirname(path), url).startsWith(repo), `unsafe relative link: ${url}`);
      file(resolve(dirname(path), url.split('#')[0]), `relative link in ${path}`);
      internal += 1;
    }
    for (const [, url] of text.matchAll(/<img\b[^>]*\bsrc="([^"]+)"/g)) {
      file(resolve(dirname(path), url), `image in ${path}`);
      internal += 1;
    }
  }
  console.log(`LINKS_OK internal=${internal} external=${externalCount} yaml=ok logo=ok (external hosts syntax-only; no network fetch)`);
} catch (error) {
  console.error(`LINKS_FAILED: ${error.message}`);
  process.exitCode = 1;
}
