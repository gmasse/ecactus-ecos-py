# eCactus ECOS Python Client

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