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
session = Ecos(datacenter="EU")
session.login("email@domain.com", "mypassword")

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
    session = AsyncEcos(datacenter="EU")
    await session.login("email@domain.com", "mypassword")

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

## Error handling

A client method raises one of three kinds of exceptions:

- **`ecactus.exceptions.EcosApiError`**, or one of its subclasses, when the API refuses
  the call or answers something the client cannot use: `AuthenticationError`,
  `UnauthorizedError`, `HomeDoesNotExistError`, `UnauthorizedDeviceError`,
  `ParameterVerificationFailedError`, `ApiResponseError`, `HttpError`,
  `InvalidJsonError`.
- **`pydantic.ValidationError`** when a successful response carries data that does not
  have the expected shape, for instance after a change on the server side. It names
  the field that failed, without the received value.
- **Transport errors**, which the client does not wrap: `requests.exceptions.RequestException`
  for `Ecos`, `aiohttp.ClientError` and `TimeoutError` for `AsyncEcos`.

```python
import pydantic
import requests

from ecactus import Ecos
from ecactus.exceptions import EcosApiError

session = Ecos(datacenter="EU", email="email@domain.com", password="mypassword")
try:
    devices = session.get_all_devices()
except EcosApiError:
    ...  # refused by the API, or an unusable response
except pydantic.ValidationError:
    ...  # data in an unexpected shape
except requests.exceptions.RequestException:
    ...  # network failure or timeout
```

## Logging

The library logs through the standard `logging` module, under the `ecactus` logger.
At `DEBUG` level it logs every API call and response, with tokens shortened to their
last 4 characters and passwords, secrets and personal data (email, phone, names,
serial numbers, location) masked, home and device IDs left in clear:

```python
import logging

logging.getLogger("ecactus").setLevel(logging.DEBUG)
```

Raw response bodies go to a separate `ecactus.wire` logger, which stays off even when
the root or `ecactus` logger is at `DEBUG`. Turn it on by naming it:

```python
logging.getLogger("ecactus.wire").setLevel(logging.DEBUG)
```

**Warning:** `ecactus.wire` output contains live access and refresh tokens. Never share it.

## Documentation

The API references for both `Ecos` and `AsyncEcos` clients, is available at:
**[eCactus ECOS API Client Documentation](https://g.masse.me/ecactus-ecos-py/api)**