#!/usr/bin/env python3
"""
Nocturne Memory — Unified Entry Point

Usage:
  python nocturne.py [command]

Commands:
  setup         Run interactive setup wizard
  stdio         Start MCP server in stdio mode (default MCP tool interface)
  sse           Start server in SSE/HTTP mode (web agents, multi-device)
  start         Auto-detect mode: SSE if stdio unavailable, else stdio

MCP clients only need to configure this ONE script as their MCP entry point.
The same script handles both stdio and SSE modes via command-line argument.

Example MCP config (all clients use the same entry point):
{
  "command": "python",
  "args": ["/path/to/nocturne.py"]
}
"""
from __future__ import annotations

import os
import sys
import argparse


def _resolve_project_root() -> str:
    """Locate the nocturne_memory project root."""
    script_path = os.path.abspath(__file__)
    return os.path.dirname(script_path)


def _load_env():
    """Load .env from project root."""
    project_root = _resolve_project_root()
    dotenv_path = os.path.join(project_root, ".env")

    # Expand ~ in DATABASE_URL to absolute path
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key == "DATABASE_URL" and "~" in value:
                    # Handle sqlite+aiosqlite://~/.x or sqlite+aiosqlite:///~/.x
                    # os.path.expanduser only expands ~ at the START of the path,
                    # so we strip leading /, expand, then re-add a single /
                    if "://" in value:
                        scheme_end = value.index("://") + 3
                        path_part = value[scheme_end:]
                        clean_part = path_part.lstrip("/")
                        expanded = os.path.expanduser(clean_part)
                        value = value[:scheme_end] + "/" + expanded.replace(os.sep, "/")
                    else:
                        value = os.path.expanduser(value)
                    os.environ[key] = value
                else:
                    os.environ[key] = value

    # Inject project root and backend into Python path
    backend_dir = os.path.join(project_root, "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


def _get_data_dir() -> str:
    """Get the configured data directory, with ~ expansion."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return os.path.join(os.path.expanduser("~"), ".nocturne-memory")

    # Extract path from sqlite+aiosqlite:///path or similar
    if "://" in db_url:
        path_part = db_url.split("://", 1)[1]
        if path_part.startswith("/"):
            return os.path.expanduser(path_part)
        return path_part

    return os.path.expanduser(db_url)


def cmd_setup():
    """Run the interactive setup wizard."""
    _load_env()
    project_root = _resolve_project_root()
    sys.path.insert(0, os.path.join(project_root, "backend"))

    import subprocess

    setup_script = os.path.join(project_root, "setup.py")
    result = subprocess.run([sys.executable, setup_script], cwd=project_root)
    sys.exit(result.returncode)


def cmd_stdio():
    """Start MCP server in stdio mode (for IDE/CLI MCP clients)."""
    _load_env()
    project_root = _resolve_project_root()
    backend_dir = os.path.join(project_root, "backend")

    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from mcp_server import mcp
    mcp.run(transport="stdio")


def cmd_sse():
    """Start server in SSE/HTTP mode (for web agents, multi-device)."""
    _load_env()
    project_root = _resolve_project_root()
    backend_dir = os.path.join(project_root, "backend")

    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from run_sse import main as sse_main
    sse_main()


def cmd_start():
    """Auto-detect: try stdio if stdin is a terminal, otherwise SSE."""
    _load_env()

    # If running in a non-interactive context (piped, redirected), use SSE
    # Otherwise default to stdio
    is_interactive = sys.stdin.isatty()

    if is_interactive:
        cmd_stdio()
    else:
        cmd_sse()


def cmd_config():
    """Print the MCP configuration snippet for the current platform."""
    project_root = _resolve_project_root()
    is_windows = os.name == "nt"

    script_path = __file__
    config = {
        "command": "python" if not is_windows else "python",
        "args": [os.path.abspath(script_path), "stdio"],
    }

    import json
    print(json.dumps(config, indent=2))
    print()
    print("# Add the above to your MCP client config (mcpServers section)")
    print("# For Claude Code:")
    print(f"#   claude mcp add-json -s user nocturne-memory '{json.dumps(config)}'")


COMMANDS = {
    "setup": cmd_setup,
    "stdio": cmd_stdio,
    "sse": cmd_sse,
    "start": cmd_start,
    "config": cmd_config,
}


def main():
    parser = argparse.ArgumentParser(
        prog="nocturne",
        description="Nocturne Memory — Long-Term Memory Server for MCP Agents",
        add_help=False,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=list(COMMANDS.keys()),
        help="Command to run (default: start)",
    )
    parser.add_argument("--help", "-h", action="help", help="Show this help message")

    args = parser.parse_args()
    COMMANDS[args.command]()


if __name__ == "__main__":
    main()
