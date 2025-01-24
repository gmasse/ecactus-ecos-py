"""Ecos API mock server."""

import asyncio
from datetime import datetime
import logging
import random
import string

from aiohttp import web

# Configure logging
logger = logging.getLogger(__name__)

class EcosMockServer:
    """Ecos API mock server class."""

    def __init__(self, host: str = '127.0.0.1', port: int = 8080, login: str = 'test@test.com', password: str = 'test'):
        """Initialize the class."""
        logger.warning('Initializing EcosMockServer')
        self.url = None
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.app = web.Application()
        self._runner = None
        base_token = f"{self._generate_random(string.ascii_letters + string.digits, 20)}.{self._generate_random(string.ascii_letters + string.digits, 155)}"
        self.access_token = base_token + self._generate_random(
            string.ascii_letters + string.digits + "-_", 86
        )
        self.refresh_token = base_token + self._generate_random(
            string.ascii_letters + string.digits + "-_", 86
        )

    @staticmethod
    def _generate_random(allowed: str, length: int):
        """Generate a random string of a specified length from a set of allowed characters.

        Args:
            allowed (str): A string of allowed characters.
            length (int): The desired length of the generated random string.

        Returns:
            str: A random string of the specified length, composed of characters from the allowed set.

        Example:
            generate_random(string.ascii_letters + string.digits, 10)

        """
        return "".join(random.choice(allowed) for _ in range(length))

    async def handle_login(self, request: web.Request):
        """Mock login endpoint."""
        output = {}
        data = await request.json()  # Parse the JSON payload
        if (
            not data.get("clientVersion")
            or data.get("clientType") != "BROWSER"
            or not data.get("email")
            or not data.get("password")
        ):
            output["code"] = 20000
            output["message"] = ""
            output["success"] = False
            output["data"] = {}
            if not data.get("clientVersion"):
                output["message"] = output["data"]["clientVersion"] = "cannot be blank"
            if data.get("clientType") != "BROWSER":
                output["message"] = output["data"]["clientType"] = (
                    "Invalid terminal type"
                )
            if not data.get("email"):
                output["message"] = output["data"]["email"] = "cannot be blank"
            if not data.get("password"):
                output["message"] = output["data"]["password"] = "cannot be blank"
        elif data.get("email") != self.login or data.get("password") != self.password:
            output = {
                "code": 20414,
                "message": "Account or password or country error",
                "success": False,
            }
        else:
            output = {
                "code": 0,
                "message": "success",
                "success": True,
                "data": {
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                },
            }
        return web.json_response(output, status=200)

    async def handle_get_user_info(self, request: web.Request):
        """Mock user info endpoint."""
        headers = await request.headers()
        if headers.get("Authorization") != self.access_token:
            return web.json_response(
                {"code": 401, "message": "Unauthorized", "success": False}, status=401
            )
        return web.json_response(
            {
                "code": 0,
                "message": "success",
                "success": True,
                "data": {
                    "username": self.login,
                    "nickname": "Test",
                    "email": self.login,
                    "phone": "",
                    "timeZoneId": "209",
                    "timeZone": "GMT-05:00",
                    "timezoneName": "America/Toronto",
                    "datacenterPhoneCode": 49,
                    "datacenter": "EU",
                    "datacenterHost": "https://api-ecos-eu.weiheng-tech.com",
                },
            },
            status=200,
        )

    async def catch_all(self, request: web.Request):
        """Catch all endpoint."""
        # if request.path starts with /api/client/ then
        if request.path.startswith("/api/client/"):
            path_after = request.path[11:]  # get the path after /api/client
            ts = int(
                datetime.now().timestamp() * 1000
            )  # get the current timestamp in milliseconds
            return web.json_response(
                {
                    "timestamp": ts,
                    "status": 404,
                    "error": "Not Found",
                    "message": "",
                    "path": path_after,
                },
                status=404,
            )
        if request.path == "/api/client":
            return web.HTTPMovedPermanently("/api/client/")  # redirect to /api/client/
        # else
        return web.HTTPBadGateway()

    def setup_routes(self):
        """Configure routes."""
        self.app.add_routes(
            [
                web.post("/api/client/guide/login", self.handle_login),
                web.get("/api/client/settings/user/info", self.handle_get_user_info),
                web.route("*", "/{path:.*}", self.catch_all),
            ]
        )

    def run(self):
        """Run the server."""
        self.setup_routes()
        self.url = f'http://{self.host}:{self.port}'
        web.run_app(self.app, host=self.host, port=self.port)

    async def start(self):
        """Start the server asynchronously."""
        self.setup_routes()
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, host=self.host, port=self.port)
        self.url = f'http://{self.host}:{self.port}'
        await site.start()

    async def stop(self):
        """Stop the server."""
        if self._runner is not None:
            await self._runner.cleanup()

"""
if __name__ == "__main__":
    server = EcosMockServer()
    server.run()
"""

async def main():
    """Run the server."""
    server = EcosMockServer()
    await server.start()
    print(f'Running server on {server.url}') # noqa: T201
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("Process interrupted") # noqa: T201
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
