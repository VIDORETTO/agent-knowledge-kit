# Test seam policy

Behavioral acceptance tests use the supported root import (`import docops`),
the CLI subprocesses, JSON artifacts and the real MCP process. In particular,
`test_public_interface.py`, `test_public_seams.py`, `test_promotion_recovery.py`
and `test_public_metrics.py` do not import implementation modules.

The `test_post_*.py` files are retained as explicitly marked
`compatibility-infrastructure` characterization tests. They exercise lease,
storage, fake-MCP and validator boundaries needed to protect the adapter during
the public-seam migration; they are not evidence that an end user must import
those modules. Vendor/security unit tests and pure policy classifiers are
similarly infrastructure tests. Any new user-visible behavior must add a
root/CLI seam test first.
