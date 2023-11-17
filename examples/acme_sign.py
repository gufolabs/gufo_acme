import asyncio
import os
import sys

from gufo.acme.clients.base import AcmeClient
from gufo.acme.types import AcmeChallenge

CHALLENGE_DIR = "/www/acme/"


class SignAcmeClient(AcmeClient):
    async def fulfill_http_01(
        self, domain: str, challenge: AcmeChallenge
    ) -> bool:
        v = self.get_key_authorization(challenge)
        with open(os.path.join(CHALLENGE_DIR, challenge.token), "wb") as fp:
            fp.write(v)
        return True

    async def clear_http_01(
        self: AcmeClient, domain: str, challenge: AcmeChallenge
    ) -> None:
        os.unlink(os.path.join(CHALLENGE_DIR, challenge.token))


async def main(
    client_state_path: str, domain: str, csr_path: str, cert_path: str
) -> None:
    with open(client_state_path, "wb") as fp:
        state = fp.read()
    with open(csr_path, "wb") as fp:
        csr = fp.read()
    async with SignAcmeClient.from_state(state) as client:
        cert = await client.sign(domain, csr)
    with open(cert_path, "wb") as fp:
        fp.write(cert)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
