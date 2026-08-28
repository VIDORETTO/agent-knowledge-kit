"""Tests for stdout protection concept used in MCP server."""

import io
import sys


class TestStdoutProtection:
    def test_stdout_redirect_mechanism(self):
        """Verify that redirecting sys.stdout to sys.stderr works correctly.

        The actual redirect happens in server.py main() before mcp.run().
        This tests the mechanism itself is sound.
        """
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        fake_stderr = io.StringIO()

        try:
            sys.stderr = fake_stderr
            sys.stdout = sys.stderr  # This is what main() does

            # Now print() should go to our fake_stderr
            print("test mcp protection")

            output = fake_stderr.getvalue()
            assert "test mcp protection" in output
            assert sys.stdout is sys.stderr
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def test_print_does_not_go_to_original_stdout(self):
        """After redirect, print() must NOT appear on original stdout."""
        original_stdout = sys.stdout
        capture_original = io.StringIO()
        fake_stderr = io.StringIO()

        try:
            sys.stdout = capture_original  # Capture "original" stdout
            sys.stdout = fake_stderr  # Now redirect (simulates main())

            print("should not be on original")

            # Check fake_stderr got it
            assert "should not be on original" in fake_stderr.getvalue()
            # Check original capture did NOT get it
            assert capture_original.getvalue() == ""
        finally:
            sys.stdout = original_stdout
