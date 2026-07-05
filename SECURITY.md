# Security

unslop is a single-file, offline text linter. It doesn't make network
calls, doesn't read credentials, and doesn't write anything besides its
own stdout. The realistic attack surface is small, but if you find
something, here's how to report it.

## Reporting a vulnerability

Please don't open a public issue for security problems. Use GitHub's
private reporting instead:

https://github.com/munzzyy/unslop/security/advisories/new

That goes straight to the maintainer and isn't visible publicly until
it's resolved. Include what you found, how to reproduce it, and the
impact you'd expect.

## Supported versions

This project doesn't maintain long-term release branches. Fixes land on
the latest tagged version; there's no backport policy.
