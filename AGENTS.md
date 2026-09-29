# Documentation maintenance

The Antora source is `docs/src/`. Run `npm --prefix docs run check-migration -- --source`
for frozen-source, page, and nav assertions; this does **not** verify rendered
diagrams or staged aliases. After generating an isolated artifact and staging its
38 legacy aliases, run `npm --prefix docs run check-migration -- --site-dir PATH`
for the full six-render/alias gate. Run `npm --prefix docs run check-links` to
validate local references and inbound documentation URLs without network access.
Never write to or remove `docs/build/` for verification.

## Documentation state

<!-- maintained by the docouture-documenting-changes skill — do not hand-edit structure, only content -->

| doc page | derived from | status |
| --- | --- | --- |
| `ROOT/pages/index.adoc` | manual (marketing home) | — |
| `main/pages/about.adoc` | manual (overview and legacy MDX) | — |
| `main/pages/architecture.adoc` | manual (architecture walkthrough and legacy MDX) | — |
| `main/pages/prerequisites.adoc` | manual (onboarding) | — |
| `main/pages/quickstart.adoc` | manual (onboarding and maintained CLI example) | — |
| `main/pages/guides-overview.adoc` | manual (guide navigation) | — |
| `main/pages/reference-overview.adoc` | manual (reference navigation) | — |
| `main/pages/additional-information.adoc` | manual (project policies) | — |
| `main/pages/contributing.adoc` | manual (contributor guidance) | — |
| `main/pages/configuration.adoc` | `packages/cerbia-core/src/cerbia/core/config.py` | current |
| `main/pages/cli.adoc` | `packages/cerbia-cli/src/cerbia/cli/{scan,validate}/_command.py` | current |
| `main/pages/gate.adoc` | `packages/cerbia-core/src/cerbia/core/security_gate/_gate.py` | current |
| `main/pages/i18n.adoc` | manual (legacy MDX and usage guidance) | — |
| `main/pages/logging.adoc` | manual (legacy MDX and usage guidance) | — |
| `main/pages/packages.adoc` | manual (package gateway) | — |
| `main/pages/components/custom-components.adoc` | manual (custom integration guide) | — |
| `main/pages/components/loaders.adoc` | manual (legacy loader catalog) | — |
| `main/pages/components/loaders/file-loader.adoc` | `packages/cerbia-core/src/cerbia/core/loaders/file.py` | current |
| `main/pages/components/loaders/text-loader.adoc` | `packages/cerbia-core/src/cerbia/core/loaders/text.py` | current |
| `main/pages/components/preprocessors.adoc` | manual (legacy preprocessor catalog) | — |
| `main/pages/components/preprocessors/speculative-decoding.adoc` | manual (legacy MDX and algorithm walkthrough) | — |
| `main/pages/components/preprocessors/whitespace-normalization.adoc` | manual (legacy MDX) | — |
| `main/pages/components/scanners.adoc` | manual (legacy scanner catalog) | — |
| `main/pages/components/scanners/canary-leak.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/canary/` | current |
| `main/pages/components/scanners/invisible-text.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/invisible_text/` | current |
| `main/pages/components/scanners/keyword.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/keyword/` | current |
| `main/pages/components/scanners/pii.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/pii/` | current |
| `main/pages/components/scanners/pii-presidio.adoc` | `packages/cerbia-presidio/src/cerbia/presidio/scanners/` | current |
| `main/pages/components/scanners/prompt-injection.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/prompt_injection/` | current |
| `main/pages/components/scanners/prompt-injection-protectai.adoc` | `packages/cerbia-protectai/src/cerbia/protectai/scanners/` | current |
| `main/pages/components/scanners/secrets.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/secret/` | current |
| `main/pages/components/scanners/url-allowlist.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/url_allowlist/` | current |
| `main/pages/components/scanners/url-malicious.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/malicious_url/` | current |
| `main/pages/components/scanners/xss.adoc` | `packages/cerbia-core/src/cerbia/core/scanners/xss/` | current |
| `main/pages/components/score-aggregators.adoc` | manual (legacy aggregator catalog) | — |
| `main/pages/components/score-aggregators/max.adoc` | `packages/cerbia-core/src/cerbia/core/score_aggregators/` | current |
| `main/pages/components/score-aggregators/max-with-bonus.adoc` | `packages/cerbia-core/src/cerbia/core/score_aggregators/` | current |
| `main/pages/components/score-aggregators/mean.adoc` | `packages/cerbia-core/src/cerbia/core/score_aggregators/` | current |
| `cerbia/pages/index.adoc` | `packages/cerbia/pyproject.toml` | current |
| `cerbia-core/pages/index.adoc` | `packages/cerbia-core/pyproject.toml`, `packages/cerbia-core/src/cerbia/core/` | current |
| `cerbia-cli/pages/index.adoc` | `packages/cerbia-cli/pyproject.toml`, `packages/cerbia-cli/src/cerbia/cli/` | current |
| `cerbia-ml/pages/index.adoc` | `packages/cerbia-ml/pyproject.toml`, `packages/cerbia-ml/src/cerbia/ml/` | current |
| `cerbia-presidio/pages/index.adoc` | `packages/cerbia-presidio/pyproject.toml`, `packages/cerbia-presidio/src/cerbia/presidio/` | current |
| `cerbia-protectai/pages/index.adoc` | `packages/cerbia-protectai/pyproject.toml`, `packages/cerbia-protectai/src/cerbia/protectai/` | current |

These statuses record the migration's source/content checks, not a live product
API audit or a successful six-diagram production render. Recheck a code-derived
row when its listed source changes; do not auto-regenerate manual pages.
