"""Tool definitions (JSON schemas) exposed to the LLM.

Each tool is described once here and shared by the agent and tests.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# run_command — execute a shell command
# ---------------------------------------------------------------------------
RUN_COMMAND_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Run a shell command on the user's machine and return "
            "stdout, stderr, and the exit code.  Use this to inspect the "
            "system, run builds, manage files, execute tests, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact command line to execute.",
                },
                "shell": {
                    "type": "string",
                    "enum": ["bash", "sh", "zsh", "cmd", "powershell"],
                    "description": (
                        "Which shell to use.  Defaults to bash on "
                        "Unix/macOS, cmd on Windows."
                    ),
                },
            },
            "required": ["command"],
        },
    },
}

# ---------------------------------------------------------------------------
# read_file — read a file from disk
# ---------------------------------------------------------------------------
READ_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Read the contents of a file on the user's machine.  "
            "Returns the text content (up to a size limit).  "
            "Use this to inspect source code, config files, logs, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Absolute or relative (to CWD) path to the file."
                    ),
                },
                "max_chars": {
                    "type": "integer",
                    "description": (
                        "Maximum characters to return.  Defaults to 8000."
                    ),
                },
            },
            "required": ["path"],
        },
    },
}

# ---------------------------------------------------------------------------
# write_file — create or overwrite a file
# ---------------------------------------------------------------------------
WRITE_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Create or overwrite a file with the given content.  "
            "Parent directories are created automatically."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Absolute or relative (to CWD) path to the file."
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
}

# ---------------------------------------------------------------------------
# edit_file — search-and-replace within a file
# ---------------------------------------------------------------------------
EDIT_FILE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "Edit an existing file by replacing the first occurrence of "
            "'old_text' with 'new_text'.  Use this for surgical edits "
            "instead of rewriting an entire file."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Absolute or relative (to CWD) path to the file."
                    ),
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to search for.",
                },
                "new_text": {
                    "type": "string",
                    "description": (
                        "The text to replace it with.  Use an empty string "
                        "to delete the matched text."
                    ),
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}

# ---------------------------------------------------------------------------
# list_files — list directory contents
# ---------------------------------------------------------------------------
LIST_FILES_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": (
            "List files and directories at a given path.  "
            "Returns names with type indicators (/ for directories)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Directory path. Defaults to the current working "
                        "directory if omitted."
                    ),
                },
                "recursive": {
                    "type": "boolean",
                    "description": (
                        "If true, list files recursively (up to a limit). "
                        "Default: false."
                    ),
                },
                "max_entries": {
                    "type": "integer",
                    "description": "Maximum entries to return. Default: 200.",
                },
            },
            "required": [],
        },
    },
}


# All tools in the order we present them to the model.
ALL_TOOLS: list[dict[str, Any]] = [
    RUN_COMMAND_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    LIST_FILES_SCHEMA,
]
