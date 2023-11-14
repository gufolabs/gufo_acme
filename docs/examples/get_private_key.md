# Gufo ACME Examples: Generating RSA Private Key

This guide will drive you through the process
of the generation of private key using
Gufo ACME library. Generation of the private
key is a first step for obtaining a signed
certificate for your domain.

```  py title="get_private_key.py" linenums="1"
--8<-- "examples/get_private_key.py"
```

The code is straightforward:

```  py title="get_private_key.py" linenums="1" hl_lines="1"
--8<-- "examples/get_private_key.py"
```

Import `sys` module to parse the CLI argument.

!!! warning

    We use `sys.argv` only for demonstration purposes. Use `argsparse` or alternatives
    in real-world applications.

```  py title="get_private_key.py" linenums="1" hl_lines="3"
--8<-- "examples/get_private_key.py"
```

Then we import an `ACMEClient` itself.

```  py title="get_private_key.py" linenums="1" hl_lines="6"
--8<-- "examples/get_private_key.py"
```
We define the `main` function to wrap our code. It assepts
a `path` parameter, containing a path to the file to store
a private key.

```  py title="get_private_key.py" linenums="1" hl_lines="7"
--8<-- "examples/get_private_key.py"
```
`ACMEClient.get_domain_private_key()` function generates
a private key in PEM format. It assepts an optional parameter
which defines a RSA key length. The default is 4096, which is
suitable for our applications. This function is the
static method, so we don't need to instantiate an
`ACMEClient`.

```  py title="get_private_key.py" linenums="1" hl_lines="8 9"
--8<-- "examples/get_private_key.py"
```
Open file for write, note the key has `bytes` type, so
we need to use `wb` option to write a binary file.
The write our private key.

```  py title="get_private_key.py" linenums="1" hl_lines="12 13"
--8<-- "examples/get_private_key.py"
```
If we're called from command line, get a first command argument
as a path and call our `main` function.

## Running

Run the example:

``` shell
python3 examples/get_private_key.py /tmp/key.pem
```

Check the `/tmp/key.pem` file:

```
-----BEGIN RSA PRIVATE KEY-----
MIIJKgIBAAKCAgEA260eTqE2jOhIMW0b9AQn08KbGMbJJGPKfAhxBfa0MIQ7g8Tb
50tWbnK+NTdEAHZCfvfwpieVDgrwVNlPW5sL14xPltJ3zcQRydJTOFpV/WImtd6j
...
xgJwpjMz0pm+9Exoe8VwmUc/gOSatoOC9DRg+hAIG7FciNUVfEeXq8ImmcDypeSe
wjBT33F36F0O22Ij4EVyW+etjp5hbboaKjjoxq/EkMTwwnET6HzpkMOj7+x/VQ==
-----END RSA PRIVATE KEY-----
```

## Conclusions
In this section we have mastered the process of the generation
of the RSA public key using helper function. Let's proceed
to next example and generate a Certificate Signed Request.