"""Tests for the tools module (schema validation)."""

from __future__ import annotations

from ai_terminal.tools import ALL_TOOLS


class TestToolSchemas:
    def test_all_tools_is_list(self):
        assert isinstance(ALL_TOOLS, list)
        assert len(ALL_TOOLS) == 5

    def test_each_tool_has_required_fields(self):
        for tool in ALL_TOOLS:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_tool_names_are_unique(self):
        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert len(names) == len(set(names))

    def test_expected_tool_names(self):
        names = {t["function"]["name"] for t in ALL_TOOLS}
        assert names == {
            "run_command",
            "read_file",
            "write_file",
            "edit_file",
            "list_files",
        }
