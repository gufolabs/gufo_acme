import sys

from gufo.acme.client import ACMEClient


def main(domain: str, private_key_path: str, csr_path: str) -> None:
    with open(private_key_path, "rb") as fp:
        pk = fp.read()
    csr = ACMEClient.get_domain_csr(domain, pk)
    with open(csr_path, "wb") as fp:
        fp.write(csr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
