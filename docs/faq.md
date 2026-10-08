---
hide:
    - navigation
---
# FAQ

## Getting Started

### What is Gufo ACME?

Gufo ACME is an asynchronous Python client for the ACME protocol (RFC 8555). It automates account registration, order creation, challenge handling, and certificate retrieval.

### Who is Gufo ACME for?

Gufo ACME is for Python developers and system administrators who want to automate certificate issuance and renewal from an ACME-compatible certificate authority.

### Which certificate authorities can I use?

Gufo ACME is designed to work with ACME-compatible certificate authorities. The project documentation lists [Let's Encrypt](https://letsencrypt.org/), [ZeroSSL](https://zerossl.com/), and Google Public CA. You select a CA by passing its ACME directory URL to the client.

### How do I install Gufo ACME?

Install the package with pip:

```shell
pip install gufo_acme
```

See the [Installation guide](installation.md) for upgrade and uninstall instructions.

### Does Gufo ACME support asyncio?

Yes. The client API is asynchronous. Use `async with` to manage a client and `await` for account, order, and signing operations.

### How do I create an ACME account?

Generate an account key, create a client with the CA's directory URL, then register a contact email. The registration example uses the Let's Encrypt staging directory:

```python
from gufo.acme.clients.base import AcmeClient

directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
key = AcmeClient.get_key()

async with AcmeClient(directory, key=key) as client:
    await client.new_account("admin@example.com")
    state = client.get_state()
```

See [Register ACME Account](examples/acme_register.md) for a complete example.

### How do I issue a certificate?

Create a domain private key and a certificate signing request (CSR), restore the registered account state, then call `sign()`. The client returns the issued certificate in PEM format. You must provide or choose a client that can fulfill a challenge for your domain. See [Signing Certificate](examples/acme_sign.md) for a complete HTTP-01 example.

## ACME Challenges and Clients

### Which ACME challenges are supported?

The base client can dispatch `http-01`, `dns-01`, and `tls-alpn-01` challenges to handler methods. A handler must implement the required provisioning and cleanup. The supplied clients implement HTTP-01 with a local web-server directory or WebDAV, and DNS-01 with the PowerDNS API.

### Which challenge types do the supplied clients support?

* `WebAcmeClient` provisions HTTP-01 token files in a directory served at `/.well-known/acme-challenge/`.
* `DavAcmeClient` provisions HTTP-01 tokens using WebDAV PUT and DELETE requests with Basic authentication.
* `PowerDnsAcmeClient` provisions DNS-01 TXT records using the PowerDNS API.

Use `AcmeClient` as a base class when you need to integrate a different web server, DNS provider, or challenge mechanism.

### Does Gufo ACME include a built-in HTTP-01 server?

No. `WebAcmeClient` writes challenge tokens to a directory; your web server must make the expected challenge URL publicly reachable. `DavAcmeClient` instead uploads and removes tokens through an existing WebDAV endpoint.

### Can I use a DNS provider other than PowerDNS?

Yes. Subclass `AcmeClient` and implement `fulfill_dns_01()` and `clear_dns_01()` to create and remove the required DNS record through your provider's API. Use `get_key_authorization()` and the `PowerDnsAcmeClient` implementation as references for the challenge value and lifecycle.

### Can I implement my own challenge handler?

Yes. Subclass `AcmeClient` and override the matching `fulfill_*` and `clear_*` methods. Return `True` from a fulfillment method when the challenge is provisioned and ready for validation; return `False` to let the client try another offered challenge.

### Does Gufo ACME support wildcard certificates?

Wildcard issuance is not a documented, ready-to-use workflow. ACME requires DNS-01 validation for wildcard identifiers, and a custom integration may need to handle wildcard authorization names specifically. Verify the behavior with your CA's staging environment before relying on wildcard issuance.

### Can I request certificates for multiple domains?

The low-level `new_order()` method accepts one domain or an iterable of domains. The high-level `sign()` method accepts one domain and a CSR, so multi-domain certificate workflows may require coordinating the order and authorization steps yourself or extending the client.

## Accounts, Keys, and Operations

### How do I save and restore an ACME account?

Call `get_state()` after account registration and store the returned bytes securely. Restore the same account with `AcmeClient.from_state(state)` (or the corresponding subclass) when issuing or renewing certificates. The serialized state contains the account private key and account URL, so treat it as a secret.

### Are the account key and certificate private key the same?

No. The account key signs ACME protocol requests. The domain private key belongs to the certificate and is used to create its CSR. Gufo ACME provides separate helpers for generating these keys.

### How do I generate a domain private key and CSR?

Use `AcmeClient.get_domain_private_key()` to generate a PEM-encoded RSA private key, then pass that key and the domain name to `AcmeClient.get_domain_csr()`. You can also generate the CSR with another tool and pass its PEM bytes to `sign()`.

### Does Gufo ACME handle challenge cleanup?

`sign()` calls the matching `clear_*` handler after an authorization becomes valid. `WebAcmeClient` and `DavAcmeClient` remove their HTTP-01 token; the current `PowerDnsAcmeClient` does not override `clear_dns_01()`, so its TXT record is left in place. A custom DNS integration should implement cleanup if it needs to remove temporary records.

### Can I test against Let's Encrypt without issuing trusted certificates?

Yes. Use the Let's Encrypt staging directory URL shown in the examples. Staging is intended for testing integrations before switching to the production directory.

### How do I handle timeouts and ACME errors?

Operations raise `AcmeError` subclasses for protocol, authorization, fulfillment, connection, and timeout failures. Catch `AcmeError` to handle ACME failures generally, or catch a specific exception such as `AcmeTimeoutError` or `AcmeFulfillmentFailed` when the application needs different recovery behavior.

### Can I change the request timeout or User-Agent?

Yes. Pass `timeout` (in seconds) and/or `user_agent` when creating the client. The default network timeout is 40 seconds.

## Development and Support

### Where can I find examples and API documentation?

The [Examples](examples/index.md) section walks through key generation, CSR creation, account registration, and certificate signing. The [Reference](reference/) documents the Python API.

### Where is the Gufo ACME source code?

The source code, tests, and issue tracker are available in the [Gufo ACME GitHub repository](https://github.com/gufolabs/gufo_acme/).

### How can I report a bug or request a feature?

Open an issue in the [GitHub repository](https://github.com/gufolabs/gufo_acme/issues). Include the ACME directory URL (without credentials), the relevant exception or log output, and steps to reproduce the problem. Do not include private keys, account state, API keys, or other secrets.

### What license does Gufo ACME use?

Gufo ACME is released under the [3-clause BSD License](LICENSE.md).

## About Gufo

### What does "Gufo" mean?

*Gufo* means *the Owl* in Italian.

### Why the owls?

We love owls, and the viable parts of our technologies were proven at the project named "the Owl".

### What is Gufo Labs?

[Gufo Labs](https://gufolabs.com/) is the Milan-based company specializing in network and IT consulting and software research.

### What is Gufo Stack?

Gufo Stack is a collection of core components extracted from the [NOC](https://getnoc.com/) project and released as independent packages under the 3-clause BSD license. These components share common quality standards and have been used under high load. See [more about Gufo Stack](https://gufolabs.com/products/gufo-stack/).
