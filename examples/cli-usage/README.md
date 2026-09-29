# CLI usage

This scenario configures the `cerbia` command-line interface with built-in
loaders, preprocessors, scanners, and a score aggregator. Install the CLI
extra before running these commands.

From this directory:

```bash
uv run cerbia validate config.cerbia.yaml
uv run cerbia scan --config config.cerbia.yaml
uv run cerbia scan --config config.cerbia.yaml --text "A short message"
```

Validation exits `0`. The safe `--text` override replaces configured loaders
and exits `0`. The final command uses the configured loaders and exits `1`
because the fixture includes an unsafe value. See the [CLI reference](https://inditextech.github.io/cerbia/prerelease/main/cli/)
and [configuration guide](https://inditextech.github.io/cerbia/prerelease/main/configuration/) for general options.
