<!--
SPDX-FileCopyrightText: INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)

SPDX-License-Identifier: Apache-2.0
-->

# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Restored the `code-uv_python-release-core` workflow to its golden bytes after
  a release attempt clobbered it (#13).
- Hardened the `docouture-*` workflows to least-privilege tokens, resolving
  the Scorecard Token-Permissions alerts on `main` (#20).

## [0.3.0] - 2026-09-30

### Fixed

- Restored the golden bytes of `.tool-versions` clobbered by a failed release
  attempt (#12).

## [0.2.0] - 2026-09-30

### Changed

- Release alignment only: bumped package versions to 0.2.0; no functional
  changes.

## [0.1.0] - 2026-09-30

### Added

- Initial release of the modular security-scanning library for AI/LLM
  pipelines: the `cerbia` metapackage plus `cerbia-core`, `cerbia-cli`,
  `cerbia-ml`, `cerbia-presidio` and `cerbia-protectai`.

### Changed

- Adopted centrally governed CI workflows.
- Migrated documentation to Docouture (#9).

### Fixed

- Normalized the trailing newline when reading `.tool-versions` inside release
  heredocs (#11).

[Unreleased]: https://github.com/InditexTech/cerbia/compare/v0.3.0...HEAD

[0.3.0]: https://github.com/InditexTech/cerbia/compare/v0.2.0...v0.3.0

[0.2.0]: https://github.com/InditexTech/cerbia/compare/v0.1.0...v0.2.0

[0.1.0]: https://github.com/InditexTech/cerbia/releases/tag/v0.1.0
