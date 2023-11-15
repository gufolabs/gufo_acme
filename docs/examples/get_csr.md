# Gufo ACME Examples: Generating Certificate Signing Request

We have mastered how to generate a private key
in our [get_private_key](get_private_key.md)
example. This guide will drive you through the
next step: the generation of the Certificate
Signing Request (CSR). The CSR is the
entity which passed to the Certificate Authority (CA)
to obtain a signed certificate for domain.

```  py title="get_csr.py" linenums="1"
--8<-- "examples/get_csr.py"
```

The code is straightforward:

```  py title="get_csr.py" linenums="1" hl_lines="1"
--8<-- "examples/get_csr.py"
```

Import `sys` module to parse the CLI argument.

!!! warning

    We use `sys.argv` only for demonstration purposes. Use `argsparse` or alternatives
    in real-world applications.

```  py title="get_csr.py" linenums="1" hl_lines="3"
--8<-- "examples/get_csr.py"
```

Then we import an `ACMEClient` itself.

```  py title="get_csr.py" linenums="1" hl_lines="6"
--8<-- "examples/get_csr.py"
```
We define the `main` function to wrap our code. It assepts
the following parameters:

* `domain` - a domain name.
* `private_key_path` - a path to private key in PEM format,
    which we have generated in out [get_private_key](get_private_key.md)
    example.
* `csr_path` - a path to store resulting CSR.

```  py title="get_csr.py" linenums="1" hl_lines="7 8"
--8<-- "examples/get_csr.py"
```
First we need to load our private key. Note we need
a `bytes` type, so we open file with `rb` option.
The `pk` variable contains our private key.

```  py title="get_csr.py" linenums="1" hl_lines="9"
--8<-- "examples/get_csr.py"
```
`ACMEClient.get_domain_csr()` function generates
a CSR in PEM format. It aceepts requred parameters:

* `domain` - domain name
* `private_key` - private key in PEM format.

The `csr` variable cotains out CSR content.


```  py title="get_csr.py" linenums="1" hl_lines="8 9"
--8<-- "examples/get_csr.py"
```
Open file for write, note the CSR has `bytes` type, so
we need to use `wb` option to write a binary file.
Then write our CSR.

```  py title="get_csr.py" linenums="1" hl_lines="14 15"
--8<-- "examples/get_csr.py"
```
If we're called from command line, get a command line arguments:

1. domain name
2. private key path
3. CSR path

## Running

Run the example:

``` shell
python3 examples/get_csr.py example.com /tmp/key.pem /tmp/csr.pem
```

Check the `/tmp/csr.pem` file:

``` title="/tmp/csr.pem"
-----BEGIN CERTIFICATE REQUEST-----
MIIEejCCAmICAQAwFjEUMBIGA1UEAwwLZXhhbXBsZS5jb20wggIiMA0GCSqGSIb3
DQEBAQUAA4ICDwAwggIKAoICAQDbrR5OoTaM6EgxbRv0BCfTwpsYxskkY8p8CHEF
...
QBsW0aHYdWwW+UJ5ApzSJh9hT87C7madmOJ9LqozPf9tDDuaYv4/Ips9EKEv9pcN
rKniaHZSBUGfBBqLq2a25E0cn19wly5FARPR1lIaEmz2sTV09AdM3kyEFM4bug==
-----END CERTIFICATE REQUEST-----
```

## Conclusions
In this section we have mastered the process of the generation
of the Certificate Signing Request. The resulting CSR
may be passed to any Certificate Authority. In our next
example we will write a simple ACME Bot to automate
the certificate siging process.