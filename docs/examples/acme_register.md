# Gufo ACME Examples: Register ACME Account

We have mastered how to create a Certificate
Signing Request in our [get_csr](get_csr.md)
example. This guide will drive you through
an ACME account registration process.
An account registration process is crucial
to perform all other operations, ACME
is intended to: The certificate signing.

```  py title="acme_register.py" linenums="1"
--8<-- "examples/acme_register.py"
```

The code is straightforward:

```  py title="acme_register.py" linenums="1" hl_lines="1"
--8<-- "examples/acme_register.py"
```

ACMEClient is an asynchronous client, so we
need `asyncio.run()` function to launch it.


```  py title="acme_register.py" linenums="1" hl_lines="2"
--8<-- "examples/acme_register.py"
```

Import `sys` module to parse the CLI argument.

!!! warning

    We use `sys.argv` only for demonstration purposes. Use `argsparse` or alternatives
    in real-world applications.

```  py title="acme_register.py" linenums="1" hl_lines="4"
--8<-- "examples/acme_register.py"
```

Then we import an `ACMEClient` itself.

```  py title="acme_register.py" linenums="1" hl_lines="6"
--8<-- "examples/acme_register.py"
```
The crucial ACME protocol concept is the *Directory*. The directory
is an URL which allows to fetch all necessary information about
ACME server. In our case we're using Letsencrypt staging directory.

!!! warning

    The staging server should be used only for testing purposes.
    Replace the `DIRECTORY` variable with the productive
    endpoint to get the real certificates.

```  py title="acme_register.py" linenums="1" hl_lines="9"
--8<-- "examples/acme_register.py"
```
We define the `main` function to wrap our code. It assepts
the following parameters:

* `email` - an account email.
* `client_state` - a path to where we can save the state
    of the client to reuse it later.

!!! note

    The main function is asynchronous

```  py title="acme_register.py" linenums="1" hl_lines="10"
--8<-- "examples/acme_register.py"
```
The client uses secret key to sign all communications to
the server. Later, this key will be bound to account.
We use `ACMEClient.get_key()` function to generate
a new key.

```  py title="acme_register.py" linenums="1" hl_lines="11"
--8<-- "examples/acme_register.py"
```
`ACMEClient` requires two mandatory parameters:

* ACME Directory URL.
* The client key.

We use `async with` construct to initialize the client
and make it available within the block.

```  py title="acme_register.py" linenums="1" hl_lines="12"
--8<-- "examples/acme_register.py"
```

We use `new_account()` call to register the new account.
Since then the client is considered *bound* and we can
use it for other operations.

```  py title="acme_register.py" linenums="1" hl_lines="13"
--8<-- "examples/acme_register.py"
```
Client key and account information is required for any
account manipulations. So we save them for later usage.


```  py title="acme_register.py" linenums="1" hl_lines="14 15"
--8<-- "examples/acme_register.py"
```
Open file for write, note the state has `bytes` type, so
we need to use `wb` option to write a binary file.
Then write our state.

```  py title="acme_register.py" linenums="1" hl_lines="18 19"
--8<-- "examples/acme_register.py"
```
If we're called from command line, get a command line arguments:

1. Account email
2. State path

## Running

Run the example:

``` shell
python3 examples/acme_register.py mymail@mydomain.com /tmp/acme.json
```

Check the `/tmp/acme.json` file:

``` title="/tmp/acme.json"
{
  "directory": "https://acme-staging-v02.api.letsencrypt.org/directory",
  "key": {
    "n": "qhd84f-9Wb...5AQQ",
    "e": "AQAB",
    "d": "Sgan5MoDNC..Fk9cw",
    "p": "6BPvgdy6_i..gkdM",
    "q": "u5_dOHJqNh..bRRs",
    "dp": "C9PYRPoG3..MVf9k",
    "dq": "LQ5U14tSS..iRIGU",
    "qi": "5AcvleFCl..jBFsQ"
  },
  "account_url": "https://acme-staging-v02.api.letsencrypt.org/acme/acct/1234567"
}
```

## Conclusions
In this section we have mastered the process of the account registration.
Now we're ready to a major ACME's step: A sertificate signing.
