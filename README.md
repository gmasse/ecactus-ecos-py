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
pip install git+https://github.com/gmasse/ecactus-ecos-py.git
```

## Usage

### Synchronous Client

```python
from ecactus import Ecos

# Initialize the client
session = Ecos(datacenter='EU')
session.login('email@domain.com', 'mypassword')

# Fetch user details
user_info = session.get_user_info()
print(user_info)

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
    user_info = await session.get_user_info()
    print(user_info)

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
