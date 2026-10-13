# Contributing

## Feature freeze until 2026-11-10

Until then, only fixes, measurements and docs get merged. New flags, detectors and agent formats wait: open an issue so they're not lost. Measurements are the most useful thing you can send now:

- a rerun of the benchmark: [REPRODUCE.md](REPRODUCE.md), then the [Benchmark rerun](https://github.com/Pazificateur69/tokenleak/issues/new?template=benchmark-rerun.yml) form;
- a week of your own sessions before and after: [My before/after](https://github.com/Pazificateur69/tokenleak/issues/new?template=compare-result.yml).

## Tests

```bash
python3 -m unittest discover -s tests
python3 skills/tokenleak/scripts/tokenleak.py --help
```

CI runs them on Linux, macOS and Windows with Python 3.13, and on Linux and Windows with Python 3.8. The code stays stdlib-only and Python 3.8 compatible. Add a test with every fix.

## Numbers

Every measured number in the docs comes from a committed folder in [bench/results](bench/results); README and BENCHMARK.md link to it, the site links to BENCHMARK.md. `summary.md` is generated from the JSON records (`python3 bench/run.py --summarize <dir>`), never edited by hand. Failed runs stay in the folder. A number from someone's own sessions says so, and gives the command that printed it.

## Releasing to PyPI

Publishing runs from `.github/workflows/publish.yml` when a GitHub release is published, with PyPI Trusted Publishing (no token stored anywhere). It stays off until the PyPI side exists. One-time setup, by the maintainer:

1. On pypi.org, sign in and add a pending trusted publisher: project `tokenleak`, owner `Pazificateur69`, repository `tokenleak`, workflow `publish.yml`, environment `pypi`.
2. On GitHub, Settings → Environments: create `pypi`. Settings → Variables → Actions: add `PYPI_PUBLISH` = `true`.
3. Bump `__version__` in `skills/tokenleak/scripts/tokenleak.py`, tag `v<version>`, publish the release. The workflow runs the tests, builds, refuses a tag that doesn't match the version, and uploads.
