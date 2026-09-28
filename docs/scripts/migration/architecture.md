# Documentation mapping

This note records where the current Fumadocs pages will live in the Docouture
site. The complete machine-readable inventory is
[`legacy-routes.json`](./legacy-routes.json). This task establishes IDs and
navigation only. It does not create the AsciiDoc pages, nav files, or Antora
module descriptors.

## Site shape

The marketing home and documentation index serve different purposes. The
separately authored `docs/app/page.tsx` maps to `ROOT:index` at `/cerbia/`.
The authored docs index `docs/content/docs/index.mdx` maps to `main:about`.
Its old `/cerbia/docs/` route remains separate and is not reused for the
marketing page.

Product-wide documentation uses six ordered groups in the `main` module:

1. **Overview** starts at `main:about` and includes the existing architecture
   page at `main:architecture`.
2. **Getting started** starts at `main:prerequisites`. The existing
   getting-started walkthrough maps to `main:quickstart` at position 2, after
   the section entry page.
3. **Guides** starts at `main:guides-overview`. No current source is recast as a
   task guide without evidence that it is procedural; the current task-like
   material remains in the closest existing walkthrough or reference topic.
4. **Reference** starts at `main:reference-overview`. Existing configuration,
   internationalization, logging, CLI, gate, component, and package-gateway
   sources, plus all 23 component topics, map here. Their positions begin at 2,
   after the section entry page at position 1.
5. **Additional information** starts at `main:additional-information`.
6. **Contributing** starts at `main:contributing`.

The entry IDs for section groups are declared in the manifest because they are
new authored pages, not among the 38 frozen source rows. Their content must be
written from repository evidence when those pages are created. The manifest
does not claim that release notes, a changelog, a FAQ, or a security contact
policy exists. Additional-information and contributing pages must state only
what the repository and its contribution/security materials support.

## Source-to-target rules

The 38 frozen rows remain one-to-one with the old authored MDX sources: eight
root topics, 23 component topics, and seven package topics. Each route row
records a target page ID, module, navigation group and position, page family,
and canonical redirect target. `oldUrl` and its slashless and `index.html`
variants remain source facts; the redirect target expresses the destination,
not a claim that the page or redirect file has already been generated.

The eight root topics are assigned by reader intent. The docs index becomes
Overview, the existing getting-started walkthrough becomes Quickstart, and
configuration, CLI, gate, i18n, and logging remain exact Reference topics.
Architecture remains a separate Overview topic because its pipeline flow and
result model have substantial independent content.

The 23 component sources stay in `main` and keep their component-topic identity.
Catalog pages for loaders, preprocessors, scanners, score aggregators, and
custom components precede their detail topics in Reference. Individual scanner,
loader, preprocessor, and aggregator pages retain their source-derived IDs and
order follows the existing `meta.json` lists. This preserves the current
component catalog while avoiding a second product-specific component module.

The seven package sources are split by role. `packages/index.mdx` becomes
`main:packages`, a compact gateway to package modules. The six package-specific
sources each become the index page in their matching module: `cerbia`,
`cerbia-core`, `cerbia-cli`, `cerbia-ml`, `cerbia-presidio`, and
`cerbia-protectai`. Package-specific install selectors, import namespaces,
optional dependencies, and API details belong in those modules, not duplicated
in main Reference.

## Content strategy

The migration keeps existing useful prose and examples, then checks factual
claims against the current repository. Primary sources are the frozen MDX
pages and their `meta.json` ordering. Product behavior and public names are
checked against package code, package metadata, tests, examples, and the root
README or contribution guide as appropriate. The historical snapshot is only a
cross-check, not a replacement for this checkout.

New section entry pages should provide useful, CerbIA-specific orientation and
links to mapped pages. They must not be empty nav placeholders. Where the
current source is thin, write a short grounded page or fold its information into
the section entry page according to the authoring guide sizing rule. Do not
invent release history, supported versions, support commitments, FAQ answers,
security-reporting channels, API symbols, or features. Mark an unsupported
claim as absent rather than filling a template with a promise.

The `main` Reference overview and package gateway should explain how to find
the detailed references. They should link to the six package modules instead
of copying their API material. The 23 component topics remain direct
`main` references, preserving a single canonical account of built-in
component behavior.

## Validation

Run `node docs/scripts/migration/check-legacy-map.mjs --source-check` to
compare the frozen source inventory, source hashes, old URLs, and Mermaid fence
locations with the local Fumadocs tree. Run
`node docs/scripts/migration/check-legacy-map.mjs --map-only` to validate
one-to-one targets, nav positions, six main groups, six package modules, and
separate marketing and docs-index destinations. Actual page and nav existence
is intentionally deferred until the content conversion and navigation tasks.
