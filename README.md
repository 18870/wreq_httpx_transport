# wreq_httpx_transport
An httpx.AsyncTransport for [wreq-python](https://github.com/0x676e67/wreq-python) library.


## Usage
See example.py.

Tested with httpx 0.28.1 and rnet v2.4.2 / v3.0.0rc / wreq v0.10.2


## Not supported features
- No sync transport (im lazy)
- Only `pool` and `read` timeout works.
- Auth, redirects aren't tested, may not work at all.