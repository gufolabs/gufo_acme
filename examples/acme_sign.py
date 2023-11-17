import asyncio
import os
import sys

from gufo.acme.clients.base import ACMEClient
from gufo.acme.types import ACMEChallenge

CHALLENGE_DIR = "/www/acme/"


class SignACMEClient(ACMEClient):
    async def fulfill_http_01(
        self, domain: str, challenge: ACMEChallenge
    ) -> bool:
        v = self.get_key_authorization(challenge)
        with open(os.path.join(CHALLENGE_DIR, challenge.token), "wb") as fp:
            fp.write(v)
        return True

    async def clear_http_01(
        self: ACMEClient, domain: str, challenge: ACMEChallenge
    ) -> None:
        os.unlink(os.path.join(CHALLENGE_DIR, challenge.token))


async def main(
    client_state_path: str, domain: str, csr_path: str, cert_path: str
) -> None:
    with open(client_state_path, "wb") as fp:
        state = fp.read()
    with open(csr_path, "wb") as fp:
        csr = fp.read()
    async with SignACMEClient.from_state(state) as client:
        cert = await client.sign(domain, csr)
    with open(cert_path, "wb") as fp:
        fp.write(cert)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
