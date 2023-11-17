---
hide:
    - navigation
---
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

To see unreleased changes, please see the [CHANGELOG on the master branch](https://github.com/gufolabs/gufo_acme/blob/master/CHANGELOG.md) guide.

## 0.2.0 - 2023-11-17

## Added

* DavAcmeClient: http-01 fulfillment using WebDAV
* PowerDnsAcmeClient: dns-01 fulfillment using PowerDNS.
* WebAcmeClient: http-01 fulfillment using static files.

## Changed

* ACMEClient has been moved into `gufo.acme.clients.base`.
* ACMEClient, types, and exceptions have been renamed to snake-case.

## Fixed

* Fixed typo in exception class name.

## 0.1.1 - 2023-11-16

### Fixed

* Fixed `AcmeClient.from_state()` to return a proper subclass.
* Fixed type annotation for `AcmeClient.__aenter__()` in subclasses.

## 0.1.0 - 2023-11-15

* Initial release.