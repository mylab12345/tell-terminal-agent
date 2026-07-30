"""Tests for the executor module."""

from __future__ import annotations

import platform

import pytest

from ai_terminal.executor import CommandResult, run_command


class TestCommandResult:
    def test_ok_when_returncode_zero(self):
        r = CommandResult("echo hi", 0, "hi\n", "")
        assert r.ok

    def test_not_ok_when_returncode_nonzero(self):
        r = CommandResult("false", 1, "", "error")
        assert not r.ok

    def test_not_ok_when_timed_out(self):
        r = CommandResult("sleep 999", 0, "", "", timed_out=True)
        assert not r.ok

    def test_combined_output_truncation(self):
        r = CommandResult("cmd", 0, "x" * 5000, "y" * 1000)
        out = r.combined_output(limit=100)
        assert len(out) < 200  # truncated
        assert "truncated" in out

    def test_combined_output_empty(self):
        r = CommandResult("cmd", 0, "", "")
        assert r.combined_output() == ""


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Unix-only test",
)
class TestRunCommandUnix:
    def test_echo(self):
        result = run_command("echo hello", shell="sh")
        assert result.ok
        assert "hello" in result.stdout

    def test_nonexistent_command(self):
        result = run_command("nonexistent_command_xyz_123", shell="sh")
        assert not result.ok

    def test_timeout(self):
        result = run_command("sleep 10", timeout=0.5, shell="sh")
        assert result.timed_out
        assert not result.ok

    def test_cwd(self, tmp_path):
        result = run_command("pwd", cwd=tmp_path, shell="sh")
        assert result.ok
        assert str(tmp_path) in result.stdout

    def test_stderr(self):
        result = run_command("echo err >&2", shell="sh")
        assert "err" in result.stderr


class TestRunCommandCrossPlatform:
    def test_auto_shell(self):
        """auto shell should pick something that works."""
        result = run_command("echo test", shell="auto")
        assert result.ok
        assert "test" in result.stdout
