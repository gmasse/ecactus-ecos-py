# Contributing

Thanks for your interest in improving the eCactus ECOS Python client! Contributions of all kinds — bug fixes, new features, and documentation — are welcome.

## Branching and pull requests

- **Target the `dev` branch.** Create your branch from `dev` and open pull requests against `dev`.
- **`main` is release-only.** It is updated only when cutting a release; please do not open feature or fix PRs against it.

```bash
git checkout dev
git pull
git checkout -b my-feature   # or fix/my-bug
```

## Development setup

```bash
git clone https://github.com/gmasse/ecactus-ecos-py.git
cd ecactus-ecos-py
python -m venv venv
source venv/bin/activate
python -m pip install '.[dev]'
```

The project supports Python **3.11 through 3.14**.

## Before submitting a pull request

Run the same checks CI runs:

```bash
ruff check                        # linting
mypy                              # type checking
pytest                            # tests
python scripts/unasync.py --check # sync client is in sync with the async one
```

### Keeping the sync client in sync

The synchronous `ecactus.Ecos` class (`src/ecactus/client.py`) is **automatically generated**
from the asynchronous `ecactus.AsyncEcos` class via [`scripts/unasync.py`](scripts/unasync.py).
If you change `AsyncEcos`, regenerate the sync client and commit the result:

```bash
python scripts/unasync.py
```

CI runs `python scripts/unasync.py --check` and will fail if the generated code is out of date.

## Documentation

Preview the documentation locally with:

```bash
mkdocs serve
```

See [README.md](README.md) for more development details and [TODO.md](TODO.md) for pending tasks.
