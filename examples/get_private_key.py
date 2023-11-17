import sys

from gufo.acme.clients.base import AcmeClient


def main(path: str) -> None:
    pk = AcmeClient.get_domain_private_key()
    with open(path, "wb") as fp:
        fp.write(pk)


if __name__ == "__main__":
    main(sys.argv[1])
