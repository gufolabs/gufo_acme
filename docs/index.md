---
template: index.html
hide:
    - navigation
    - toc
hero:
    title: Gufo ACME
    subtitle: The Python asyncio client for the ACME protocol
    install_button: Getting Started
    source_button: Source Code
---
# Gufo ACME

*Gufo ACME is a Python asyncio client for the ACME protocol.*

The Automatic Certificate Management Environment (ACME) protocol defines a method
for automated certificate signing, now widely used by services
such as Let's Encrypt. Gufo ACME is a Python asyncio ACME client library that
simplifies the protocol complexity with a straightforward and robust API.

Gufo ACME contains various clients which can be applied to your tasks:

* [AcmeClient][gufo.acme.clients.base.AcmeClient] - base client to implement any fulfillment functionality
    by creating subclasses.
* [DavAcmeClient][gufo.acme.clients.dav.DavAcmeClient] - http-01 fulfillment using WebDAV methods.
* [PowerDnsAcmeClient][gufo.acme.clients.powerdns.PowerDnsAcmeClient] - dns-01 PowerDNS fulfillment.
* [WebAcmeClient][gufo.acme.clients.web.WebAcmeClient] - http-01 static file fulfillment.

## Supported Certificate Authorities

* [Letsencrypt](https://letsencrypt.org)
* [ZeroSSL](https://zerossl.com/)
* Google Public CA
* Any [RFC-8555](https://tools.ietf.org/html/rfc8555) compatible CA.

## Examples

### Account Creation

Create an account and store state to the file.
``` python
client_key = AcmeClient.get_key()
async with AcmeClient(DIRECTORY, key=client_key) as client:
    await client.new_account(email)
    state = client.get_state()
with open(client_state_path, "wb") as fp:
    fp.write(state)
```

### Private Key Generation

To generate a private key in PEM format.
``` python
private_key = AcmeClient.get_domain_private_key()
```

### Generate CSR

To generate a certificate signing request.
``` python
csr = AcmeClient.get_domain_csr(domain, private_key)
```

### Sign Certificate

Sign the certificate using `http-01` challenge:

``` python
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

    ...
async with SignAcmeClient.from_state(state) as client:
    cert = await client.sign(domain, csr)
```

## Virtues

* Pure-Python implementation.
* Asynchronous.
* Fully typed.
* Clean API.
* Robust well-tested code.
* 99+% test coverage.

## On Gufo Stack

This product is a part of [Gufo Stack][Gufo Stack] - the collaborative effort 
led by [Gufo Labs][Gufo Labs]. Our goal is to create a robust and flexible 
set of tools to create network management software and automate 
routine administration tasks.

To do this, we extract the key technologies that have proven themselves 
in the [NOC][NOC] and bring them as separate packages. Then we work on API,
performance tuning, documentation, and testing. The [NOC][NOC] uses the final result
as the external dependencies.

[Gufo Stack][Gufo Stack] makes the [NOC][NOC] better, and this is our primary task. But other products
can benefit from [Gufo Stack][Gufo Stack] too. So we believe that our effort will make 
the other network management products better.

[Gufo Labs]: https://gufolabs.com/
[Gufo Stack]: https://docs.gufolabs.com/
[NOC]: https://getnoc.com/