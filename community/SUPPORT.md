# Support policy

The supported profiles and platforms are declared in
[`docs/SUPPORT-MATRIX.json`](../docs/SUPPORT-MATRIX.json). Core support covers
Python 3.11–3.13 on Ubuntu, Windows and macOS. Formats, wheel, bootstrap,
RAG/MCP and filesystem guarantees are separate profiles; an optional profile
is not silently treated as core support.

For a support request, include the candidate version or commit, operating
system, Python version, profile, exact command, sanitized output and a minimal
synthetic reproduction. Never attach private corpora, indexes, model caches,
tokens or credentials. Security issues belong in the private process described
in `SECURITY.md`, not in a public issue.

The project does not promise support for unlisted harnesses, Python versions,
network transports or remote model repositories.
