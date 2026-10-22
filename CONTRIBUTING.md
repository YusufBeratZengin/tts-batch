# Contributing

Use Python 3.10 or newer. Keep runtime dependencies optional and preserve local,
offline operation. Do not add automatic engine, model or voice downloads.

```sh
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m unittest discover -v
```

Tests also run without installing the package or development dependencies.
Run discovery from the repository root. Scratch files are confined to ignored
`is/test-tmp/`. Mock subprocess engines and optional packages; generate small WAV
fixtures in Python. Never add model weights, generated narration, private scripts
or credentials to a contribution.

For behavior changes, add focused tests covering observable results. Preserve
integer-frame timing, validate audio formats and document any manifest schema
change. Keep English and Turkish READMEs consistent. New engines implement the
protocol in `src/tts_batch/engines.py`; include all synthesis options in their
cache identity. Engine/model licenses must remain separate from this package.

Use small Conventional Commits, for example `fix: preserve decimal sentence
boundaries`. Pull requests should explain the problem, resulting behavior and
commands actually used for validation. Report unavailable checks honestly.

Report bugs at
[the issue tracker](https://github.com/YusufBeratZengin/tts-batch/issues), with
Python/OS versions, engine version and a minimal synthetic script. Include no
personal information or private model assets. See [SECURITY.md](SECURITY.md)
for security reports.
