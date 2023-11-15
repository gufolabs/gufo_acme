# Gufo ACME Examples: Signing Certificate

We have mastered how to create an ACME server
account in our [acme_register](acme_register.md)
example. Now it is time to bring all pieces
together and get a signed certificate for our
domain.

The ACME protocol requires that the client
will prove the ownership of the domain
by one of available means, called challenge.
In out example we will use `http-01` type
of challenge which requires the client
will obtain a token from ACME server and
made it available via well-known URL like
`http://<domain>/.well-known/acme-challenges/<token>`.

We consider you have a Nginx server set up and running
with config like this:

``` title="/etc/nginx/conf.d/<domain>"
server {
  listen 80;
  server_name <domain>;
  
  location /.well-known/acme-challenge/ {
    alias /www/acme/;
  }
}
```

So our task is:

1. Get a token for domain.
2. Place file into `/www/acme/` directory.
3. Ask the server to perform validation.
4. Grab the certificate.

The ACME protocol is quite complex and really
require much more stages, but, luckily,
Gufo ACME hides all the complexity
and provides clean API.

```  py title="acme_sign.py" linenums="1"
--8<-- "examples/acme_sign.py"
```
The code is straightforward:

```  py title="acme_sign.py" linenums="1" hl_lines="1"
--8<-- "examples/acme_sign.py::6"
```

ACMEClient is an asynchronous client, so we
need `asyncio.run()` function to launch it.

```  py title="acme_sign.py" linenums="1" hl_lines="2"
--8<-- "examples/acme_sign.py::6"
```

Import `os` module which is required to join paths.

```  py title="acme_sign.py" linenums="1" hl_lines="3"
--8<-- "examples/acme_sign.py::6"
```

Import `sys` module to parse the CLI argument.

!!! warning

    We use `sys.argv` only for demonstration purposes. Use `argsparse` or alternatives
    in real-world applications.

```  py title="acme_sign.py" linenums="1" hl_lines="5"
--8<-- "examples/acme_sign.py::6"
```

Then we import an `ACMEClient` itself.

```  py title="acme_sign.py" linenums="1" hl_lines="6"
--8<-- "examples/acme_sign.py::6"
```
We also need an `ACMEChallenge` type.

```  py title="acme_sign.py" linenums="6" hl_lines="3"
--8<-- "examples/acme_sign.py:6:11"
```
The crucial ACME protocol concept is the *Directory*. The directory
is an URL which allows to fetch all necessary information about
ACME server. In our case we're using Letsencrypt staging directory.

!!! warning

    The staging server should be used only for testing purposes.
    Replace the `DIRECTORY` variable with the productive
    endpoint to get the real certificates.

```  py title="acme_sign.py" linenums="11" hl_lines="1"
--8<-- "examples/acme_sign.py:11:23"
```
We need to provide the implementation of the challenge
fulfillment. The Gufo ACME's API provides special
methods which can be overriden in subclasses to
implement the desired behavior. So we are creating
a subclass of `ACMEClient`.

```  py title="acme_sign.py" linenums="11" hl_lines="2 3 4"
--8<-- "examples/acme_sign.py:11:23"
```
We're implementing `http-01` challenge, so we need to override
`fulfill_http_01` method. This is an asyncronous method
so we use any async function inside. It accepts two parameters:

* `domain` - a domain name.
* `challenge` - a ACMEChallenge structure, which has
    a `token` field, containing challenge token.

Function returns `True` when fulfillment has beed processed correctly,
or `False`, if we wan't provide a fulfillment.

```  py title="acme_sign.py" linenums="11" hl_lines="5"
--8<-- "examples/acme_sign.py:11:23"
```
According the ACME protocol, we need to place a specially formed
data to prove our authority. The data contain challenge token and
the fingerprint of the client's key. The calculation may be tricky,
but Gufo ACME provides a `ACMEClient.get_key_authorization()` method,
which performs all necessary calculations. So we pass `challenge`
parameter and grab an authorization data as value of the variable `v`.

```  py title="acme_sign.py" linenums="11" hl_lines="6 7"
--8<-- "examples/acme_sign.py:11:23"
```
We're building real file name by adding token's value to `CHALLENGE_DIR`.
The autrorization key has type `bytes` so we open the file in `wb` mode.

```  py title="acme_sign.py" linenums="11" hl_lines="8"
--8<-- "examples/acme_sign.py:11:23"
```
Finally, we return `True` to sigalize, we have performed fulfillment
and ready to start validation.

```  py title="acme_sign.py" linenums="11" hl_lines="10 11 12"
--8<-- "examples/acme_sign.py:11:23"
```
The ACME protocol definition exlicitly notes that client may
clean up prepared data after the validation. `ACMEClient`
allows to add own cleanup code by overriding `cleanup_*`
methods. In our case we're overriding `clear_http_01` method.
Just like `fulfill_http_01`, it accepts two parameters:

* `domain` - a domain name.
* `challenge` - a ACMEChallenge structure, which has
    a `token` field, containing challenge token.

```  py title="acme_sign.py" linenums="11" hl_lines="13"
--8<-- "examples/acme_sign.py:11:23"
```
We're removing the file created in the `fulfill_http_01` method.

```  py title="acme_sign.py" linenums="26" hl_lines="1 2 3"
--8<-- "examples/acme_sign.py:26:36"
```
We define the `main` function to wrap our code. It assepts
the following parameters:

* `client_state_path` - a path to a client's state we have created
    in our [acme_register](acme_register.md) example.
* `domain_name` - our domain name.
* `csr_path` - a path to the CSR we have created in our
    [get_csr](get_csr.md) example.
* `cert_path` - a path to where we must write a resulting certificate.

!!! note

    The main function is asynchronous

```  py title="acme_sign.py" linenums="26" hl_lines="4 5"
--8<-- "examples/acme_sign.py:26:36"
```
We're reading client state from `client_state_path`. The state
is binary so we're opening the file in `rb` mode.

```  py title="acme_sign.py" linenums="26" hl_lines="6 7"
--8<-- "examples/acme_sign.py:26:36"
```
We're reading CSR from `csr_path`. The state
is binary so we're opening the file in `rb` mode.

```  py title="acme_sign.py" linenums="26" hl_lines="8"
--8<-- "examples/acme_sign.py:26:36"
```
We're instantiating `ACMEClient` directly from state by
using `from_state()` method. Note, we're restoring state
not into the `ACMEClient`, but in our `SignACMEClient` subclass.
The new `client` instance
loads the private key, directory, and account information
directly from state.

```  py title="acme_sign.py" linenums="26" hl_lines="9"
--8<-- "examples/acme_sign.py:26:36"
```
And finally, we call an `ACMEClient.sign` method, which
accepts domain name and CSR. The `sign` method simple
hides all the protocol's complexity and simply returns
us a signed certificate in PEM format.

```  py title="acme_sign.py" linenums="26" hl_lines="10 11"
--8<-- "examples/acme_sign.py:26:36"
```
We're writing a result into the output file. The certificate
has type bytes and we're opening the file in `wb` mode.


```  py title="acme_sign.py" linenums="39" hl_lines="1 2"
--8<-- "examples/acme_sign.py:39:"
```
If we're called from command line, get a command line arguments:

1. Client's state path
2. Domain name
3. CSR path
4. Certificate path

## Running

Run the example:

``` shell
python3 examples/acme_sign.py /tmp/acme.json mydomain.com /tmp/csr.pem /tmp/cert.pem
```

Check the `/tmp/cert.pem` file:

``` title="/tmp/cert.pem"
-----BEGIN CERTIFICATE-----
MIIFZTCCA00CFGMFCNLNSJLkcnJn4XJUGhtHh5JXMA0GCSqGSIb3DQEBCwUAMG8x
CzAJBgNVBAYTAklUMQ8wDQYDVQQIDAZNaWxhbm8xDzANBgNVBAcMBk1pbGFubzES
...
+pqFSNi9tsBy/T9zdVa4giUW68Zc3ezN+t+bvD/qNvAsH+c2ajR8utK0ehv+FpGH
nOfZOASlIEp2te2A6bhHqUqh7LIydzg4YV7FSnfoabO2wDbnHGESZ63/FkyYJHxH
SgFIpXon3mbTvYkSMk+ToN9Fr0n795G37W2pylEfXI28IJ4KpajiheA=
-----END CERTIFICATE-----
```

## Conclusions
In this section we have finally tied all pieces together and
wrote a simple certificate signing bot. Refer to the
[Reference](../reference/gufo/acme/index.md) for further details.
