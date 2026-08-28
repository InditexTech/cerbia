# Programmatic usage

This scenario builds a `SecurityGate` directly in Python and scans one safe and
one prompt-injection text value with the built-in `KeywordScanner`.

From this directory, run:

```bash
uv run python direct_scan.py
```

The sample prints each verdict's `is_safe` value, score, and rationale. The
safe entry passes; the prompt-injection entry is blocked by the default keyword
patterns.

See the [gate behavior documentation](https://inditextech.github.io/cerbia/docs/gate) and the
[scanner reference](https://inditextech.github.io/cerbia/docs/components/scanners) for general concepts.
