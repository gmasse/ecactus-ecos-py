# Contributing

Thanks for your interest in improving the eCactus ECOS Python client! Contributions of all kinds — bug fixes, new features, and documentation — are welcome.

## Branching and pull requests

- **Target the `dev` branch.** Create your branch from `dev` and open pull requests against `dev`.
- **`main` only receives releases and maintainer hotfixes.** Please do not open feature or fix PRs against it.
- **Pull requests are squash-merged.** The PR title becomes the commit subject on `dev`, so please write it as a [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/) (`fix: ...`, `feat(client): ...`).

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
python -m pip install --upgrade pip   # dependency groups need pip >= 25.1
python -m pip install . --group dev
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

## Releasing

Maintainers only.

1. Bump `version` in `pyproject.toml` on `dev` and refresh the lockfile (`uv lock`).
2. Open a `dev` -> `main` pull request titled `chore(release): X.Y.Z` and merge it with a
   merge commit, never a squash or a rebase. Pass the subject explicitly, since GitHub's
   default is `Merge pull request #N from ...`:

   ```bash
   gh pr merge N --merge --subject "chore(release): X.Y.Z (#N)" --body "One line per highlight."
   ```

   The merge commit keeps `dev` an ancestor of `main`, so the next release only carries
   new work and `dev` needs no syncing afterwards.
3. Tag the merge commit and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

4. Publish the GitHub release for that tag.

Publishing the release triggers [`publish.yml`](.github/workflows/publish.yml),
which builds the distributions and uploads them to PyPI through [trusted
publishing](https://docs.pypi.org/trusted-publishers/). There is no API token to
manage: PyPI verifies the workflow's OIDC identity and issues a short-lived
upload credential.

## Hotfixes

Maintainers only.

An urgent fix can go straight to `main`. Dependabot security updates always do, since
they ignore the `target-branch: dev` setting. Squash-merge the pull request into `main`,
then merge `main` back into `dev` right away so that `dev` keeps everything `main` has:

```bash
git switch main && git pull --ff-only
git switch dev && git pull --ff-only
git merge main
git push
```

To publish a code fix, bump `version` in the same pull request, then tag `main` and publish
the release as in steps 3 and 4 above.

Never rebase or force-push `main` or `dev`: contributors' clones and forks track them.
