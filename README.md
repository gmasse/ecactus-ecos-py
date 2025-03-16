# eCactus ECOS Python Client
[![ci](https://github.com/gmasse/ecactus-ecos-py/actions/workflows/ci.yml/badge.svg)](https://github.com/gmasse/ecactus-ecos-py/actions/workflows/ci.yml)

This Python client provides both synchronous and asynchronous interfaces to interact with the eCactus ECOS platform from WEIHENG Group for energy management. However, **this project is in its early stages, is not fully tested, and is not safe for production use**. Use it at your own risk.


## Features

- **Synchronous Access**: Use the `Ecos` class for straightforward, blocking operations.
- **Asynchronous Access**: Use the `AsyncEcos` class for non-blocking, concurrent operations.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install ecactus-ecos-py
```

## Usage

### Synchronous Client

```python
from ecactus import Ecos

# Initialize the client
session = Ecos(datacenter='EU')
session.login('email@domain.com', 'mypassword')

# Fetch user details
user = session.get_user()
print(user)

# Retrieve all the devices
devices = session.get_all_devices()
print(devices)
```

### Asynchronous Client

```python
import asyncio
from ecactus import AsyncEcos

async def main():
    # Initialize the client
    session = AsyncEcos(datacenter='EU')
    await session.login('email@domain.com', 'mypassword')

    # Fetch user details
    user = await session.get_user()
    print(user)

    # Retrieve all the devices
    devices = await session.get_all_devices()
    print(devices)

asyncio.run(main())
```

## Examples

A set of ready-to-use scripts is available in the `examples/` directory.

## Documentation

The API references for both `Ecos` and `AsyncEcos` clients, is available at:
**[eCactus ECOS API Client Documentation](https://g.masse.me/ecactus-ecos-py/api)**

## Development & Contributing

To set up the project for development, clone the repository and install dependencies:
```
git clone https://github.com/gmasse/ecactus-ecos-py.git
cd ecactus-ecos-py
python -m venv venv
source venv/bin/activate
python -m pip install '.[dev]'
```

We invite you to contribute to the project by opening an issue or pull request to propose new features, fix bugs, or enhance the documentation.

For pending tasks and improvements, please check the [TODO.md](TODO.md) file.

### Automatic Synchronous Code Generation

The `ecactus.Ecos` synchronous class, defined in [src/ecactus/client.py](src/ecactus/client.py), is **automatically generated** from the `ecactus.AsyncEcos` class using [scripts/unasync.py](scripts/unasync.py). When making changes to the `ecactus.AsyncEcos` class, you should re-run this script to regenerate the `ecactus.Ecos` class:
```
python scripts/unasync.py
```

This ensures that both the synchronous and asynchronous APIs remain consistent.

To verify that the generated synchronous class matches the asynchronous class, use the `--check` option:
```
python scripts/unasync.py --check
```
This will report any differences between the two classes, allowing you to catch any inconsistencies before submitting your changes.

### Code Quality

- **Linting**: Run `ruff` to check for code style issues:
  ```bash
  ruff check
  ```
- **Typing Checks**: Use `mypy` to ensure type correctness:
  ```bash
  mypy
  ```
- **Unit Tests**: Run `pytest` to execute tests:
  ```bash
  pytest
  ```

### Documentation Contribution

Use mkdocs to serve a local preview of the documentation:
```
mkdocs serve
```

## License

This project is licensed under the GPL-3.0 License. See the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

- This project is **not affiliated with, endorsed by, or associated with WEIHENG Group, eCactus, ECOS, or any related companies**.
- The names *WEIHENG*, *eCactus*, and *ECOS* may be **registered trademarks** of their respective owners.
- This software is developed **independently** and does not interact with any proprietary or official services provided by WEIHENG Group or eCactus.
