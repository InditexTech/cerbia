#!/usr/bin/env node
import assert from 'node:assert/strict';
import { constants } from 'node:fs';
import { lstatSync, openSync, realpathSync, readFileSync, closeSync, fstatSync, ftruncateSync, writeSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const basePath = '/cerbia/';
const versions = ['prerelease', 'stable'];
const urlOrigin = 'https://cerbia.invalid';

function inspectPath(path, kind, siteRoot) {
  const info = lstatSync(path);
  assert.ok(!info.isSymbolicLink(), `symbolic links are not allowed in generated site paths: ${path}`);
  assert.ok(kind === 'directory' ? info.isDirectory() : info.isFile(), `expected ${kind}: ${path}`);
  const realPath = realpathSync(path);
  const relativePath = relative(siteRoot, realPath);
  assert.ok(relativePath === '' || (!isAbsolute(relativePath) && relativePath !== '..' && !relativePath.startsWith(`..${sep}`)),
    `generated search path resolves outside selected site: ${path}`);
  return realPath;
}

function inspectSearchPaths(siteDir, version) {
  const siteInfo = lstatSync(siteDir);
  assert.ok(!siteInfo.isSymbolicLink() && siteInfo.isDirectory(), `site output must be a real directory, not a symlink: ${siteDir}`);
  const siteRoot = realpathSync(siteDir);
  inspectPath(join(siteRoot, version), 'directory', siteRoot);
  inspectPath(join(siteRoot, version, 'index.html'), 'file', siteRoot);
  inspectPath(join(siteRoot, '_'), 'directory', siteRoot);
  inspectPath(join(siteRoot, '_', 'search'), 'directory', siteRoot);
  const indexPath = join(siteRoot, '_', 'search', `ROOT-${version}.json`);
  inspectPath(indexPath, 'file', siteRoot);
  return { siteRoot, indexPath };
}

function readIndex(path) {
  const descriptor = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const opened = fstatSync(descriptor);
    const current = lstatSync(path);
    assert.ok(opened.isFile() && !current.isSymbolicLink()
      && opened.dev === current.dev && opened.ino === current.ino,
    `search index changed during validation: ${path}`);
    return { contents: readFileSync(descriptor, 'utf8'), device: opened.dev, inode: opened.ino };
  } finally {
    closeSync(descriptor);
  }
}

function validateEncoding(value, rawUrl) {
  assert.ok(!/%(?![a-fA-F0-9]{2})/.test(value), `malformed percent escape in search URL: ${rawUrl}`);
  for (const [, escape] of value.matchAll(/%([a-fA-F0-9]{2})/g)) {
    assert.equal(escape, escape.toUpperCase(), `lowercase percent escape in search URL: ${rawUrl}`);
    assert.ok(!/^[A-Za-z0-9._~-]$/.test(String.fromCharCode(Number.parseInt(escape, 16))),
      `unnecessary percent encoding in search URL: ${rawUrl}`);
  }
}

function validateSuffix(suffix, rawUrl) {
  assert.ok(!/[\u0000-\u0020\\]/.test(suffix), `noncanonical whitespace or backslash in search URL: ${rawUrl}`);
  validateEncoding(suffix, rawUrl);
  let parsed;
  try {
    parsed = new URL(rawUrl, urlOrigin);
  } catch {
    assert.fail(`invalid search URL: ${rawUrl}`);
  }
  assert.equal(parsed.origin, urlOrigin, `search URL must be same-origin path or absolute HTTP(S): ${rawUrl}`);
  assert.equal(parsed.username, '', `credentials are not valid in a search URL: ${rawUrl}`);
  assert.equal(parsed.password, '', `credentials are not valid in a search URL: ${rawUrl}`);
  assert.equal(`${parsed.search}${parsed.hash}`, suffix, `noncanonical query or fragment encoding in search URL: ${rawUrl}`);
}

function normalizeRecordUrl(url, version) {
  assert.ok(!/[\u0000-\u0020\\]/.test(url), `noncanonical whitespace or backslash in search URL: ${url}`);
  if (/^https?:\/\//i.test(url)) {
    let parsed;
    try {
      parsed = new URL(url);
    } catch {
      assert.fail(`invalid absolute search URL: ${url}`);
    }
    assert.ok(parsed.protocol === 'http:' || parsed.protocol === 'https:', `unsupported search URL scheme: ${url}`);
    assert.equal(parsed.username, '', `credentials are not valid in a search URL: ${url}`);
    assert.equal(parsed.password, '', `credentials are not valid in a search URL: ${url}`);
    assert.equal(parsed.href, url, `noncanonical absolute search URL: ${url}`);
    const rawAbsolute = url.slice(url.indexOf('://') + 3);
    const authority = rawAbsolute.replace(/[/?#].*$/, '');
    const resource = rawAbsolute.slice(authority.length) || '/';
    const delimiter = resource.search(/[?#]/);
    const pathname = (delimiter === -1 ? resource : resource.slice(0, delimiter)) || '/';
    const suffix = delimiter === -1 ? '' : resource.slice(delimiter);
    assert.equal(parsed.pathname, pathname, `absolute search URL path is normalized by URL parsing: ${url}`);
    validateEncoding(pathname, url);
    validateEncoding(suffix, url);
    assert.equal(`${parsed.search}${parsed.hash}`, suffix, `absolute search URL suffix is noncanonical: ${url}`);
    return url;
  }

  assert.ok(url.startsWith('/'), `search URL must be an absolute path: ${url}`);
  const delimiter = url.search(/[?#]/);
  const rawPath = delimiter === -1 ? url : url.slice(0, delimiter);
  const suffix = delimiter === -1 ? '' : url.slice(delimiter);
  validateSuffix(suffix, url);
  validateEncoding(rawPath, url);

  const parsed = new URL(url, urlOrigin);
  assert.equal(parsed.pathname, rawPath, `search URL path is normalized by URL parsing: ${url}`);

  if (rawPath === basePath.slice(0, -1) || rawPath === basePath) return url;

  const mountedPrefix = `${basePath}${version}/`;
  const sourcePrefix = `/${version}/`;
  let versionedPath;
  let normalizedPrefix;
  if (rawPath.startsWith(mountedPrefix)) {
    versionedPath = rawPath.slice(mountedPrefix.length);
    normalizedPrefix = mountedPrefix;
  } else if (rawPath.startsWith(sourcePrefix)) {
    versionedPath = rawPath.slice(sourcePrefix.length);
    normalizedPrefix = `${basePath}${version}/`;
  } else if (rawPath.startsWith(basePath)) {
    assert.ok(rawPath.startsWith(`${basePath}_/`), `unexpected mounted search URL: ${url}`);
    validateAssetPath(rawPath.slice(basePath.length), url);
    return url;
  } else if (rawPath.startsWith('/_/')) {
    validateAssetPath(rawPath.slice(1), url);
    return url;
  } else {
    assert.fail(`unexpected search URL for ${version}: ${url}`);
  }

  if (versionedPath) validatePathSegments(versionedPath, url);
  else assert.ok(rawPath === mountedPrefix || rawPath === sourcePrefix, `unexpected empty version page path: ${url}`);
  return `${normalizedPrefix}${versionedPath}${suffix}`;
}

function validatePathSegments(path, url) {
  assert.ok(path.endsWith('/'), `search URL path must end with a slash: ${url}`);
  const segments = path.slice(0, -1).split('/');
  assert.ok(segments.length > 0 && segments.every((segment) => /^[a-z0-9-]+$/.test(segment)),
    `noncanonical search URL path segments: ${url}`);
}

function validateAssetPath(path, url) {
  const segments = path.split('/');
  assert.ok(segments.length > 1 && segments[0] === '_'
    && segments.slice(1).every((segment) => segment !== '.' && segment !== '..' && /^[a-z0-9._-]+$/.test(segment)),
    `noncanonical search asset path: ${url}`);
}

function parseArgs(args) {
  assert.ok(args.length === 4 || args.length === 5, 'usage: fix-search-index.mjs --site-dir OUTPUT --version VERSION [--allow-build-dir]');
  assert.equal(args[0], '--site-dir');
  assert.equal(args[2], '--version');
  assert.ok(versions.includes(args[3]), `unsupported version: ${args[3]}`);
  assert.ok(args.length === 4 || args[4] === '--allow-build-dir', 'unexpected search-index fixer option');
  return { siteDir: resolve(args[1]), version: args[3], allowBuildDir: args.length === 5 };
}

function main() {
  const { siteDir, version: selectedVersion, allowBuildDir } = parseArgs(process.argv.slice(2));
  const buildSiteDir = join(repoRoot, 'docs/build/site');
  if (allowBuildDir) {
    assert.equal(siteDir, buildSiteDir, '--allow-build-dir only permits the standard docs/build/site output');
  } else {
    assert.ok(siteDir !== join(repoRoot, 'docs/build') && !siteDir.startsWith(`${join(repoRoot, 'docs/build')}/`),
      'never rewrite docs/build during verification; pass an isolated Antora output directory');
  }
  const { siteRoot, indexPath } = inspectSearchPaths(siteDir, selectedVersion);

  let updatedRecords = 0;
  const original = readIndex(indexPath);
  const index = JSON.parse(original.contents);
  assert.ok(Array.isArray(index.records), `invalid Docouture search index: ${indexPath}`);
  for (const record of index.records) {
    if (typeof record.url !== 'string') continue;
    const normalized = normalizeRecordUrl(record.url, selectedVersion);
    if (normalized !== record.url) updatedRecords += 1;
    record.url = normalized;
  }
  const serialized = `${JSON.stringify(index)}\n`;
  const finalPaths = inspectSearchPaths(siteDir, selectedVersion);
  assert.equal(finalPaths.siteRoot, siteRoot, 'selected site root changed during validation');
  assert.equal(finalPaths.indexPath, indexPath, 'search index path changed during validation');
  const descriptor = openSync(indexPath, constants.O_WRONLY | constants.O_NOFOLLOW);
  try {
    const opened = fstatSync(descriptor);
    const current = lstatSync(indexPath);
    assert.ok(opened.isFile() && !current.isSymbolicLink()
      && opened.dev === current.dev && opened.ino === current.ino
      && opened.dev === original.device && opened.ino === original.inode,
    `search index changed during validation: ${indexPath}`);
    ftruncateSync(descriptor, 0);
    const buffer = Buffer.from(serialized, 'utf8');
    let offset = 0;
    while (offset < buffer.length) {
      offset += writeSync(descriptor, buffer, offset, buffer.length - offset);
    }
  } finally {
    closeSync(descriptor);
  }

  console.log(`SEARCH_INDEX_BASEPATH_OK files=1 updatedRecords=${updatedRecords} version=${selectedVersion} mount=${basePath} site=${siteRoot}`);
}

try {
  main();
} catch (error) {
  console.error(`SEARCH_INDEX_BASEPATH_FAILED: ${error.message}`);
  process.exitCode = 1;
}
