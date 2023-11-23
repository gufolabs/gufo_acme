#  Python modules
import asyncio
import os
import tempfile
from pathlib import Path

# Gufo AcmeE modules
from gufo.acme.clients.web import WebAcmeClient
from gufo.acme.types import AcmeChallenge

from .utils import KEY, LE_STAGE_DIRECTORY

DOMAIN = "example.com"
AUTH_KEY = (
    b"qPsDhTbvumL6q2DryepIyzJS1nMkghS92IqI4mug-7c.IoRaMHpsTJikEnDg70XhS0d7Xx1ZU3Tz"
    b"MzhTKFITfwY"
)


def test_web() -> None:
    async def inner():
        chall = AcmeChallenge(
            type="http-01",
            url="xxx",
            token="qPsDhTbvumL6q2DryepIyzJS1nMkghS92IqI4mug-7c",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            client = WebAcmeClient(LE_STAGE_DIRECTORY, key=KEY, path=path)
            r = await client.fulfill_http_01(DOMAIN, chall)
            assert r is True
            with open(path / chall.token, "rb") as fp:
                data = fp.read()
            assert data == AUTH_KEY
            await client.clear_http_01(DOMAIN, chall)
            assert not os.path.exists(path / Path(chall.token))

    asyncio.run(inner())
