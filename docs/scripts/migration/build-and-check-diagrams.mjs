#!/usr/bin/env node

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const docsRoot = join(repoRoot, 'docs');
const antoraEntrypoint = join(docsRoot, 'node_modules/antora/bin/antora');
const checker = join(docsRoot, 'scripts/migration/check-diagrams.mjs');
const searchIndexFixer = join(docsRoot, 'scripts/migration/fix-search-index.mjs');

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const name = argv[index].slice(2);
    assert.ok(argv[index].startsWith('--'), `unexpected argument: ${argv[index]}`);
    assert.ok(['mode', 'playbook', 'version', 'page-id'].includes(name), `unknown option --${name}`);
    assert.ok(!Object.hasOwn(options, name), `duplicate option --${name}`);
    const value = argv[index + 1];
    assert.ok(value && !value.startsWith('--'), `missing value for --${name}`);
    options[name] = value;
    index += 1;
  }
  assert.ok(options.mode === 'sample' || options.mode === 'full', 'usage: build-and-check-diagrams.mjs --mode sample|full --playbook PLAYBOOK --version VERSION [--page-id MODULE:PAGE]');
  assert.ok(options.playbook === 'antora-playbook.local.yml' || options.playbook === 'antora-playbook.yml', 'unsupported Antora playbook');
  assert.ok(options.version && /^[A-Za-z0-9._-]+$/.test(options.version), 'invalid --version');
  if (options.mode === 'sample') assert.ok(options['page-id'], 'sample mode requires --page-id');
  else assert.ok(!options['page-id'], 'full mode does not accept --page-id');
  return options;
}

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit' });
  if (result.error) throw result.error;
  if (result.signal) throw new Error(`${command} was terminated by ${result.signal}`);
  return result.status ?? 1;
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`DIAGRAM_BUILD_FAILED: ${error.message}`);
    process.exitCode = 1;
    return;
  }

  const outputDir = mkdtempSync(join(tmpdir(), 'cerbia-antora-diagrams-'));
  try {
    const failureLevel = options.mode === 'sample' ? 'fatal' : 'warn';
    const buildExit = run(process.execPath, [
      antoraEntrypoint,
      'generate',
      '--fetch',
      '--log-failure-level', failureLevel,
      '--log-level', 'info',
      '--to-dir', outputDir,
      options.playbook,
    ], docsRoot);
    if (buildExit !== 0) {
      process.exitCode = buildExit;
      return;
    }
    if (!existsSync(join(outputDir, options.version, 'index.html'))) {
      console.error(`DIAGRAM_BUILD_FAILED: Antora exited ${buildExit} without producing ${options.version}/index.html`);
      process.exitCode = 1;
      return;
    }

    const searchFixExit = run(process.execPath, [searchIndexFixer, '--site-dir', outputDir, '--version', options.version], docsRoot);
    if (searchFixExit !== 0) {
      process.exitCode = searchFixExit;
      return;
    }

    const checkArgs = [checker, '--mode', options.mode, '--site-dir', outputDir, '--version', options.version];
    if (options['page-id']) checkArgs.push('--page-id', options['page-id']);
    process.exitCode = run(process.execPath, checkArgs, docsRoot);
  } catch (error) {
    console.error(`DIAGRAM_BUILD_FAILED: ${error.message}`);
    process.exitCode = 1;
  } finally {
    rmSync(outputDir, { recursive: true, force: true });
  }
}

main();
