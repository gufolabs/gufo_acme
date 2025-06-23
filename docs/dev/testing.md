# Building and Testing

Before starting building and testing package set up 
[Developer's Environment](environment.md) first.
From here and below we consider the shell's current
directory matches the project's root directory.

## Building Package

To test the package build run:

```
$ python -m build --sdist --wheel
```

Compiled packages will be available in the `dist/` directory.

## Running tests

To run the test suit:

```
$ pytest -vv
```

## Running Lints

All lints are checked as part of GitHub Actions Workflow. You may run lints
manually before committing to the project.

### Check Formatting

[Python Code Formatting](codequality.md#python-code-formatting) is the mandatory
requirement in our [Code Quality](codequality.md) standards. To check code
formatting run:

```
$ black --check examples/ src/ tests/
```

To fix formatting errors run:
```
$ black examples/ src/ tests/
```

We recommend setting python code formatting on file saving
(Done in [VS Code Dev Container](environment.md#visual-studio-code-dev-container)
out of the box).

### Python Code Lints

[Python Code Linting](codequality.md#python-code-linting) is the mandatory
requirement in our [Code Quality](codequality.md) standards. To check code
for linting errors run:

```
$ ruff examples/ src/ tests/
```

### Python Code Static Checks

[Python Code Static Checks](codequality.md#python-code-static-checks) is the mandatory
requirement in our [Code Quality](codequality.md) standards. To check code
for typing errors run:

```
$ mypy --strict src/
```

## Preparing a Testing Environment

The Gufo ACME test suite includes a real-world scenario for signing a certificate
using the Letsencrypt staging environment.

Gufo Labs provides all the necessary infrastructure
to run tests in the CI environment. On local environments, the test is skipped by default.

To enable the test in your local environment, additional
infrastructure is needed.

### DavAcmeClient

1. Have control over a DNS zone (later `<mydomain>`).
2. Set up an Nginx server.

Start by creating a testing `A` record (e.g., `acme-ci`), pointing
to your Nginx server.

```
acme-ci IN A <nginx ip>
```

Next, prepare a configuration file and place it in your
Nginx config directory (`/etc/nginx/conf.d/acme-ci`,
depending on your distribution).

``` title="/etc/nginx/conf.d/acme-ci"
server {
  listen 80;
  server_name acme-ci.<domain>;
  access_log  /var/log/nginx/acme-ci.<domain>.access.log timed_upstream;
  error_log  /var/log/nginx/acme-ci.<domain>.error.log;
  
  location /.well-known/acme-challenge/ {
    alias /www/acme-ci/;
    dav_methods PUT DELETE;
    limit_except GET {
    auth_basic "Staging area";
    auth_basic_user_file "/etc/nginx/auth/acme-ci"; 
    }
  }
}
```

Then create a directory for tokens

```
mkdir /www/acme-ci
chmod 700 /www/acme-ci
chown nginx /www/acme-ci
```

After that, prepare a password for authorization:

Create a separate directory:

```
mkdir /etc/nginx/auth
```

Generate a password:
```
openssl rand 21 | base64
```
And remember it.

Then create a password file, replacing <user> and <password>
with the desired username and the generated password.

```
htpasswd -b /etc/nginx/auth/acme-ci <user> <password>
```

Finally, reload and Nginx:

```
service nginx reload
```

Check the setup:

```
curl -X PUT -d "777" --user "<user>:<password>" http://acme-ci.<domain>/.well-known/acme-challenge/777
```

The file /www/acme-ci/777 should appear.

Your environment is now ready. Before running the test suite, execute the following
commands in your development environment:

```
export CI_ACME_TEST_DOMAIN=acme-ci.<domain>
export CI_DAV_TEST_DOMAIN=acme-ci.<domain>
export CI_DAV_TEST_USER=<user>
export CI_DAV_TEST_PASSWORD=<password>
```

### PowerDnsAcmeClient

We're considering:

* We're perform testig on csr-proxy-test.<domain>
* Your PowerDNS server's name is pdns.<domain>

First, in zone `<domain>` create a glue record pointing to your PowerDNS server:

```
csr-proxy-test IN IS pdns.<domain>
```

Create `csr-proxy-test.<domain>` zone:

```
pdnsutil create-zone csr-proxy-test.gufolabs.com
```

Your environment is now ready. Before running the test suite, execute the following
commands in your development environment:

```
export CI_POWERDNS_TEST_DOMAIN=csr-proxy-test.<domain>
export CI_POWERDNS_TEST_API_URL=https://<power-dns-url>
export CI_POWERDNS_TEST_API_KEY=<api key>

```



## Python Test Code Coverage Check

To evaluate code coverage run tests:

```
$ coverage run -m pytest -vv
```

To report the coverage after the test run:

```
$ coverage report
```

To show line-by-line coverage:

```
$ coverage html
```

Then open `dist/coverage/index.html` file in your browser.

## Building Documentation

To rebuild and check documentation run

```
$ mkdocs serve
```

We recommend using [Grammarly][Grammarly] service to check
documentation for common errors.

[Grammarly]: https://grammarly.com/