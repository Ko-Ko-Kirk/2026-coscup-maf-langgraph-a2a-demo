# Contributing

Contributions are welcome when they preserve the controlled comparison.

## Development setup

```bash
uv sync --locked --all-groups
./scripts/check.sh
```

## Comparison rules

Changes to one framework implementation should answer:

1. Does the other implementation need the equivalent behavior?
2. Does the change alter the prompt, tool schema, Foundry model, or A2A skill?
3. Is the difference a genuine framework capability that should remain visible?

Update `tests/test_parity.py` and `docs/source-code-comparison.md` when the
comparison contract changes.

## Pull requests

- Keep credentials and customer data out of commits and test fixtures.
- Add offline tests for protocol and runtime changes.
- Link official documentation or source for framework-specific claims.
- Do not call preview or beta features generally available.
- Run Ruff, Pyright, and Pytest before submitting.

