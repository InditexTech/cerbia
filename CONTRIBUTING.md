<!--
SPDX-FileCopyrightText: 2026 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)

SPDX-License-Identifier: Apache-2.0
-->

# Contributing

Thank you for your interest in contributing to this project! We value and appreciate any contributions you can make.
To maintain a collaborative and respectful environment, please consider the following guidelines when contributing to this project.

## Prerequisites

- Before starting to contribute to the code, you must first sign the
  Contributor License Agreement (CLA).
  Detailed instructions on how to proceed can be found [here](https://github.com/InditexTech/foss/blob/main/CONTRIBUTING.md).

## How to Contribute

1. Open an issue to discuss and gather feedback on the feature or fix you wish to address.
2. Fork the repository and clone it to your local machine.
3. Create a new branch to work on your contribution: `git checkout -b your-branch-name`.
4. Make the necessary changes in your local branch.
5. Ensure that your code follows the established project style and formatting guidelines.
6. Perform testing to ensure your changes do not introduce errors.
7. Make clear and descriptive commits that explain your changes.
8. Push your branch to the remote repository: `git push origin your-branch-name`.
9. Open a pull request describing your changes and linking the corresponding issue.
10. Await comments and discussions on your pull request. Make any necessary modifications based on the received feedback.
11. Once your pull request is approved, your contribution will be merged into the main branch.

## Contribution Guidelines

- All contributors are expected to follow the project's [code of conduct](CODE_OF_CONDUCT.md). Please be respectful and
considerate towards other contributors.
- Before starting work on a new feature or fix, check existing [issues](../../issues) and [pull requests](../../pulls)
to avoid duplications and unnecessary discussions.
- If you wish to work on an existing issue, comment on the issue to inform other contributors that you are working on it.
This will help coordinate efforts and prevent conflicts.
- It is always advisable to discuss and gather feedback from the community before making significant changes to the
project's structure or architecture.
- Ensure a clean and organized commit history. Divide your changes into logical and descriptive commits. We recommend to use the [Conventional Commits Specification](https://www.conventionalcommits.org/en/v1.0.0/)
- Document any new changes or features you add. This will help other contributors and project users understand your work
and its purpose.
- Be sure to link the corresponding issue in your pull request to maintain proper tracking of contributions.
- Remember to add license and copyright information following the [REUSE Specification](https://reuse.software/spec/#copyright-and-licensing-information).

## Development

Bootstrap the locked development environment and install the commit hook:

```bash
make install
```

Use `make format` to apply Ruff formatting in place. `make lint` is
non-mutating: it runs Ruff, ty, and a formatting check. `make verify` runs the
non-mutating lint-and-test gate.

```bash
make format
make lint
make test
make build
make verify

make test cerbia-ml
make verify cerbia-ml
make build cerbia-ml
```

Accepted package names are `cerbia`, `cerbia-core`, `cerbia-ml`,
`cerbia-presidio`, and `cerbia-protectai`. `make install` synchronizes the
complete locked workspace. The metadata-only `cerbia` package is handled
automatically without source coverage.

To prepare a release, use a canonical PEP 440 version:

```bash
make bump-version 1.2.3
```

This updates every package version and internal CerbIA dependency pin, then
refreshes `uv.lock` and synchronizes the workspace environment.

CI runs each package pipeline in parallel. The local hooks run Ruff and ty
through uv, so no globally installed Python tooling is required.

### Documentation

Documentation uses Docouture and Antora. Install Node.js 24 or later, npm, and
Docker with a running daemon. The site renders Mermaid diagrams through a local
Kroki service; the Antora extension starts it with Docker Compose when needed.
From the repository root, install locked dependencies, build the site with
persistent output, or start the live development server:

```bash
make docs-install
make docs-build
make docs-serve
```

The equivalent commands from `docs/` are:

```bash
npm ci
npm run build
npm run check-links
npm run dev
```

`make docs-build` uses the production playbook (`main` and `docs/stable`) and leaves
`docs/build/site` for the generated Linkinator checker and gh-pages publisher.
Stop `npm run dev` before building: the live server owns that output while running.
The checker fails on broken external links and warns on local or configured
non-representative links. No deployment command is needed for local QA.

For HEAD-only QA without touching the live output, run from `docs/`:

```bash
output=$(mktemp -d)
trap 'rm -rf "$output"' EXIT
npx antora --fetch --log-failure-level warn --to-dir "$output" antora-playbook.local.yml
node scripts/fix-search-index.mjs --site-dir "$output"
node --test scripts/fix-search-index.test.mjs
```

Run the generated checker in a temporary repository copy with its own
`build/site` to avoid crawling or modifying the live server's output.

Docouture publishes the prerelease from `main` and the stable version from the
`docs/stable` tag. The production playbook retains CerbIA's site URL, branding,
UI, extensions, and modules; only its content refs align with that standalone
policy. The production build runs the search-index fixer over every generated
index because Docouture 1.1.1 omits `/cerbia/` from search record URLs. The
standalone release does not require `docs/.release-version`.

The build does not check diagram count or SVG accessibility. Kroki failures may
fall back to raw Mermaid without failing Antora; a successful build is not proof
that diagrams rendered. `docouture dev` uses the upstream live-build path and does
not run the production search post-step.
