import asyncio
import sys

from gufo.acme.clients.base import ACMEClient

DIRECTORY = "https://acme-staging-v02.api.letsencrypt.org/directory"


async def main(email: str, client_state_path: str) -> None:
    client_key = ACMEClient.get_key()
    async with ACMEClient(DIRECTORY, key=client_key) as client:
        await client.new_account(email)
        state = client.get_state()
    with open(client_state_path, "wb") as fp:
        fp.write(state)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
