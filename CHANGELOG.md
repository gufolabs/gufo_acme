---
hide:
    - navigation
---
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

To see unreleased changes, please see the [CHANGELOG on the master branch](https://github.com/gufolabs/gufo_acme/blob/master/CHANGELOG.md) guide.

## 0.5.1 - 2025-09-08

### Security

* devcontainer: Install security patches.
* devcontainer: Use python:3.13-slim-trixie as base.

### Infrastructure

* devcontainer: Bump IPython to 9.4.0.

## 0.5.0 - 2025-06-23

### Added

* AcmeClient.get_self_signed_certificate funciton.

### Infrastructure

* Replace black with ruff format.
* PYPI trusted publishing.

## 0.4.0 - 2023-11-23

### Added

* `AcmeAuthorizationStatus` structure

### Changed

* `AcmeClient.get_challenges` replaced with `AcmeClient.get_authorization_status`.
* Respond to challenges only if authorization status is `pending`.

## 0.3.0 - 2023-11-23

### Added

* External Account Binding support.

## 0.2.0 - 2023-11-17

### Added

* DavAcmeClient: http-01 fulfillment using WebDAV
* PowerDnsAcmeClient: dns-01 fulfillment using PowerDNS.
* WebAcmeClient: http-01 fulfillment using static files.

### Changed

* ACMEClient has been moved into `gufo.acme.clients.base`.
* ACMEClient, types, and exceptions have been renamed to snake-case.

### Fixed

* Fixed typo in exception class name.

## 0.1.1 - 2023-11-16

### Fixed

* Fixed `AcmeClient.from_state()` to return a proper subclass.
* Fixed type annotation for `AcmeClient.__aenter__()` in subclasses.

## 0.1.0 - 2023-11-15

* Initial release.