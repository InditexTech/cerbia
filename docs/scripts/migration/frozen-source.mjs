import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';

// Task 1's committed snapshot predates the migration; it stays available after MDX deletion.
const baseline = 'c67457d4d1b1ebcc6ce608657ee148271eb730fa';
const prefix = 'docs/content/docs/';
const gitOptions = (repoRoot) => ({ cwd: repoRoot, env: { ...process.env, GIT_MASTER: '1' }, maxBuffer: 1024 * 1024 });

export function frozenSource(repoRoot, row, sourceRoot = join(repoRoot, prefix)) {
  const path = row.source;
  assert.ok(path === 'docs/app/page.tsx' || /^docs\/content\/docs\/(?:[a-z0-9-]+\/)*[a-z0-9-]+\.mdx$/.test(path), `invalid frozen source path: ${path}`);
  const root = resolve(repoRoot, prefix);
  const selectedRoot = resolve(sourceRoot);
  const local = path.startsWith(prefix) ? resolve(selectedRoot, path.slice(prefix.length)) : resolve(repoRoot, path);
  assert.ok(local.startsWith(`${path.startsWith(prefix) ? selectedRoot : resolve(repoRoot)}/`), `source escapes root: ${path}`);
  let contents;
  if (existsSync(local)) {
    contents = readFileSync(local);
  } else {
    // An explicit fixture root must never silently fall back to the historical tree.
    assert.equal(selectedRoot, root, `missing source in fixture: ${path}`);
    try {
      contents = execFileSync('git', ['show', `${baseline}:${path}`], gitOptions(repoRoot));
    } catch {
      throw new Error(`missing committed frozen source: ${path}`);
    }
  }
  assert.equal(createHash('sha256').update(contents).digest('hex'), row.sha256, `frozen source hash mismatch: ${path}`);
  return contents.toString('utf8');
}

export function frozenSourcePaths(repoRoot, sourceRoot) {
  if (existsSync(sourceRoot)) {
    function walk(dir) {
      return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) return walk(path);
        return entry.isFile() && entry.name.endsWith('.mdx') ? [`${prefix}${relative(sourceRoot, path).split(sep).join('/')}`] : [];
      });
    }
    return walk(sourceRoot).sort();
  }
  assert.equal(resolve(sourceRoot), resolve(repoRoot, prefix), 'missing source fixture root');
  const tracked = execFileSync('git', ['ls-tree', '-r', '--name-only', baseline, '--', prefix], { ...gitOptions(repoRoot), encoding: 'utf8' });
  return tracked.trim().split('\n').filter((path) => path.endsWith('.mdx')).sort();
}

export function frozenMetadata(repoRoot, path, sourceRoot) {
  assert.match(path, /^docs\/content\/docs\/components\/[a-z0-9-]+\/meta\.json$/);
  const root = resolve(repoRoot, prefix, 'components');
  const selectedRoot = resolve(sourceRoot);
  const local = resolve(selectedRoot, path.slice('docs/content/docs/components/'.length));
  assert.ok(local.startsWith(`${selectedRoot}/`), 'metadata path escapes source root');
  if (existsSync(local)) return readFileSync(local, 'utf8');
  assert.equal(selectedRoot, root, 'missing metadata in fixture');
  return execFileSync('git', ['show', `${baseline}:${path}`], { ...gitOptions(repoRoot), encoding: 'utf8' });
}
