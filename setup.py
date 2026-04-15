#!/usr/bin/env python3
"""
Nocturne Memory — Interactive Setup Wizard

Run with: python setup.py
Or via: python nocturne.py setup
"""
from __future__ import annotations

import os
import sys
import shutil
import sqlite3
import subprocess


# ─── Pretty output helpers ────────────────────────────────────────────────────

def _color(code: str, text: str) -> str:
    """Apply ANSI color code to text (no-op on non-TTY)."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


GREEN = lambda t: _color("32", t)
YELLOW = lambda t: _color("33", t)
RED = lambda t: _color("31", t)
CYAN = lambda t: _color("36", t)
BOLD = lambda t: _color("1", t)


def println(msg="", color=None):
    text = str(msg)
    if color:
        text = color(text)
    print(text, file=sys.stderr)


def section(title: str):
    println()
    println(BOLD(f"─── {title} "))


def step(label: str):
    print(f"  {CYAN('●')} {label}", file=sys.stderr)


def info(label: str):
    print(f"    {label}", file=sys.stderr)


def success(msg: str):
    println(f"  {GREEN('✓')} {msg}")


def warn(msg: str):
    println(f"  {YELLOW('!')} {msg}")


def error(msg: str):
    println(f"  {RED('✗')} {msg}")


# ─── Input helpers ────────────────────────────────────────────────────────────

def _prompt(msg: str, default: str = "") -> str:
    """Prompt user for input with default."""
    suffix = f" [{default}]" if default else ""
    result = input(f"  {msg}{suffix}: ").strip()
    return result or default


def _confirm(msg: str, default: bool = True) -> bool:
    """Ask yes/no question."""
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        result = input(f"  {msg}{suffix}: ").strip().lower()
        if not result:
            return default
        if result in ("y", "yes"):
            return True
        if result in ("n", "no"):
            return False
        println("  Please answer y or n.", RED)


def _select(msg: str, options: list, default: int = 0) -> str:
    """Present numbered options and return selected."""
    println(f"  {msg}")
    for i, opt in enumerate(options, 1):
        marker = " ← default" if i - 1 == default else ""
        print(f"    {i}. {opt}{marker}", file=sys.stderr)
    while True:
        result = input(f"  Choice [{default + 1}]: ").strip()
        if not result:
            return options[default]
        try:
            idx = int(result) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        println("  Invalid choice.", RED)


# ─── Core logic ──────────────────────────────────────────────────────────────

def _resolve_project_root() -> str:
    """Find project root: this file is at <project>/setup.py."""
    return os.path.dirname(os.path.abspath(__file__))


def _resolve_data_dir(raw: str) -> str:
    """Expand ~ in path and return absolute path."""
    expanded = os.path.expanduser(raw)
    return os.path.abspath(expanded)


def _ensure_data_dir(data_dir: str) -> str:
    """Create data directory and initialize empty SQLite database if missing."""
    os.makedirs(data_dir, exist_ok=True)
    println(f"  Data directory: {data_dir}")

    db_path = os.path.join(data_dir, "memory.db")

    if not os.path.exists(db_path):
        # Create new empty SQLite database
        sqlite3.connect(db_path).close()
        info(f"Created new empty database at {db_path}")
    else:
        info(f"Using existing database at {db_path}")

    return db_path


def _check_python_version() -> bool:
    """Verify Python version >= 3.10."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    error(f"Python {version.major}.{version.minor} detected. Python 3.10+ required.")
    return False


def _install_dependencies(project_root: str) -> bool:
    """Install Python dependencies via pip."""
    req_file = os.path.join(project_root, "backend", "requirements.txt")
    if not os.path.exists(req_file):
        warn(f"requirements.txt not found at {req_file}, skipping.")
        return False

    step("Installing Python dependencies...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            success("Dependencies installed")
            return True
        else:
            error(f"pip install failed: {result.stderr}")
            return False
    except Exception as e:
        error(f"Failed to run pip: {e}")
        return False


def _create_directory_link(target_dir: str, link_path: str) -> str:
    """Create a directory symlink, falling back to a junction on Windows."""
    try:
        os.symlink(target_dir, link_path, target_is_directory=True)
        return "symlink"
    except OSError as exc:
        if os.name != "nt" or getattr(exc, "winerror", None) != 1314:
            raise

        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link_path, target_dir],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or str(exc)
            raise OSError(detail) from exc
        return "junction"


def _write_env_file(project_root: str, data_dir: str, web_port: str, auto_open: bool) -> str:
    """Generate .env file with auto-expanded paths."""
    env_path = os.path.join(project_root, ".env")

    # SQLite path uses forward slashes (works on all platforms)
    db_url = f"sqlite+aiosqlite:///{data_dir.replace(os.sep, '/')}/memory.db"

    lines = [
        "# Nocturne Memory — Environment Configuration",
        "# Generated by setup.py. Edit manually if needed.",
        "",
        f"DATABASE_URL={db_url}",
        f"WEB_PORT={web_port}",
        f"AUTO_OPEN_BROWSER={'true' if auto_open else 'false'}",
        "SKIP_FRONTEND_BUILD=false",
        "",
        "# Valid memory domains (comma-separated)",
        "VALID_DOMAINS=core,writer,game,notes",
        "",
        "# Core memories loaded on system://boot",
        "CORE_MEMORY_URIS=core://agent,core://my_user,core://agent/my_user",
        "",
    ]

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    success(f".env written: {env_path}")
    return env_path


def _install_claude_code_skill(project_root: str) -> bool:
    """Copy the project skill into ~/.agents and link it into ~/.claude."""
    skill_src = os.path.join(project_root, "skills", "nocturne-memory")
    if not os.path.isdir(skill_src):
        info(f"Skill directory not found: {skill_src}, skipping.")
        return False

    agents_skill_root = os.path.join(os.path.expanduser("~"), ".agents", "skills")
    skill_dest = os.path.join(agents_skill_root, "nocturne-memory")
    claude_skill_root = os.path.join(os.path.expanduser("~"), ".claude", "skills")
    claude_skill_link = os.path.join(claude_skill_root, "nocturne-memory")

    try:
        os.makedirs(agents_skill_root, exist_ok=True)
        shutil.copytree(skill_src, skill_dest, dirs_exist_ok=True)
        success(f"Skill copied to: {skill_dest}")

        os.makedirs(claude_skill_root, exist_ok=True)
        if os.path.lexists(claude_skill_link):
            try:
                if os.path.samefile(claude_skill_link, skill_dest):
                    success(f"Claude skill link already exists: {claude_skill_link}")
                    return True
            except OSError:
                pass

            if os.path.islink(claude_skill_link):
                os.unlink(claude_skill_link)
            else:
                warn(f"Cannot create Claude skill symlink; path already exists: {claude_skill_link}")
                info("Remove or rename that path, then rerun setup.")
                return False

        link_kind = _create_directory_link(skill_dest, claude_skill_link)
        success(f"Claude skill {link_kind} created: {claude_skill_link}")
        return True
    except Exception as e:
        warn(f"Failed to install skill: {e}")
        info("You can install it manually:")
        info(f"  Copy directory: {skill_src} -> {skill_dest}")
        info(f"  Symlink: {claude_skill_link} -> {skill_dest}")
        return False


def _detect_mcp_client() -> str:
    """Try to detect which MCP client the user is running."""
    # Check common client config locations
    candidates = {
        "Cursor": [
            os.path.expanduser("~/.cursor/mcp.json"),
            os.path.expanduser("~/.cursor/settings/extend.toml"),
        ],
        "Claude Desktop": [
            os.path.expanduser("~/AppData/Roaming/Claude/claude_desktop_config.json"),
            os.path.expanduser("~/.config/Claude/claude_desktop_config.json"),
        ],
        "Windsurf": [
            os.path.expanduser("~/.codeium/windsurf/mcp_config.json"),
        ],
        "GitHub Copilot": [
            os.path.expanduser("~/.github-copilot/hosts.json"),
        ],
        "Cline": [
            os.path.expanduser("~/.cline/mcp_settings.json"),
        ],
        "VS Code": [
            os.path.expanduser("~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/代理人.json"),
        ],
    }

    found = []
    for client, paths in candidates.items():
        for p in paths:
            if os.path.exists(p):
                found.append(client)
                break

    if not found:
        return "Unknown (you'll need to add the config manually)"

    return ", ".join(found)


def _print_mcp_config(project_root: str):
    """Print the MCP configuration snippet."""
    script_path = os.path.abspath(__file__)
    nocturne_path = os.path.dirname(script_path)  # project root
    nocturne_py = os.path.join(nocturne_path, "nocturne.py").replace(os.sep, "/")

    is_windows = os.name == "nt"
    client = _detect_mcp_client()

    println()
    section("MCP Configuration")
    println(f"Detected client: {CYAN(client)}")
    println()
    println("Add this to your MCP client configuration:")
    println()

    if is_windows:
        config_windows = f'''{{
  "mcpServers": {{
    "nocturne-memory": {{
      "command": "python",
      "args": ["{nocturne_py}", "stdio"]
    }}
  }}
}}'''
        println(config_windows)
    else:
        config_unix = f'''{{
  "mcpServers": {{
    "nocturne-memory": {{
      "command": "python3",
      "args": ["/path/to/nocturne.py", "stdio"]
    }}
  }}
}}'''
        println(config_unix)

    println()
    println("For Claude Code, run:")
    println(f"  {CYAN('claude mcp add-json -s user nocturne-memory')} '\\{nocturne_py},stdio'")
    println()
    println("Claude Code: Install the optional skill to auto-inject the system prompt.")
    println()


def _print_next_steps(project_root: str, skill_installed: bool):
    """Print usage instructions."""
    println()
    section("Next Steps")
    println()
    println("  1. Add the MCP configuration above to your client")
    println("  2. Restart your MCP client")
    println("  3. Say to your AI:")
    println("     " + CYAN('"Read system://boot. Tell me who you are."'))
    println()
    if skill_installed:
        println("  Claude Code skill linked at ~/.claude/skills/nocturne-memory")
        println("  (Source copy stored at ~/.agents/skills/nocturne-memory/)")
    else:
        println("  Claude Code skill not installed.")
        println("  Re-run setup later to copy ~/.agents/skills/nocturne-memory and")
        println("  symlink it into ~/.claude/skills/nocturne-memory.")
    println()
    println("  Admin UI (Dashboard): http://localhost:8233/")
    println()
    println("  To start manually:")
    println(f"    python nocturne.py stdio      {YELLOW('# MCP stdio mode')}")
    println(f"    python nocturne.py sse         {YELLOW('# SSE/HTTP mode')}")
    println(f"    python nocturne.py config      {YELLOW('# print MCP config')}")
    println()
    println(f"  Data directory: {CYAN(_get_env_data_dir())}")
    println()


def _get_env_data_dir() -> str:
    """Read the data directory from existing .env."""
    project_root = _resolve_project_root()
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    if "://" in url:
                        path_part = url.split("://", 1)[1]
                        return os.path.expanduser(path_part)
    return os.path.join(os.path.expanduser("~"), ".nocturne-memory")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    println()
    println(BOLD("╔══════════════════════════════════════════════╗"))
    println(BOLD("║   Nocturne Memory — Setup Wizard             ║"))
    println(BOLD("╚══════════════════════════════════════════════╝"))
    println()

    project_root = _resolve_project_root()
    os.chdir(project_root)

    # Step 1: Python version
    section("Step 1 — Python Version")
    step("Checking Python...")
    if not _check_python_version():
        error("Python 3.10+ is required. Aborting.")
        sys.exit(1)
    success("Python OK")

    # Step 2: Data directory
    section("Step 2 — Data Directory")
    default_data_dir = os.path.join(os.path.expanduser("~"), ".nocturne-memory")
    raw_data_dir = _prompt(
        "Where should memory data be stored? (~ expands to home dir)",
        default_data_dir,
    )
    abs_data_dir = _resolve_data_dir(raw_data_dir)
    step(f"Using: {abs_data_dir}")

    if _confirm(f"Create directory and initialize?", default=True):
        db_path = _ensure_data_dir(abs_data_dir)
        success(f"Initialized at {db_path}")
    else:
        error("Setup cancelled.")
        sys.exit(1)

    # Step 3: Port & browser
    section("Step 3 — Admin UI")
    web_port = _prompt("Admin UI port", "8233")
    auto_open = _confirm("Open Admin UI in browser automatically?", default=False)

    # Step 4: Dependencies
    section("Step 4 — Dependencies")
    has_pip = shutil.which("pip") or shutil.which("pip3")
    if has_pip:
        _install_dependencies(project_root)
    else:
        warn("pip not found. Install dependencies manually:")
        info(f"  pip install -r {project_root}/backend/requirements.txt")

    # Step 5: Write .env
    section("Step 5 — Configuration")
    _write_env_file(project_root, abs_data_dir, web_port, auto_open)

    # Step 6: Install Claude Code skill (auto-injects system prompt)
    section("Step 6 — Optional Claude Code Skill")
    agents_skill_dir = os.path.join(os.path.expanduser("~"), ".agents", "skills", "nocturne-memory")
    claude_skill_dir = os.path.join(os.path.expanduser("~"), ".claude", "skills", "nocturne-memory")
    info(f"Copy to: {agents_skill_dir}")
    info(f"Symlink to: {claude_skill_dir}")
    skill_installed = False
    if _confirm(
        "Install Claude Code skill (copy to ~/.agents/skills and symlink into ~/.claude/skills)?",
        default=False,
    ):
        skill_installed = _install_claude_code_skill(project_root)
    else:
        info("Skipped. You can install it later with:")
        info("  python nocturne.py setup")

    # Step 7: Print MCP config
    _print_mcp_config(project_root)

    # Step 8: Done
    section("Setup Complete")
    _print_next_steps(project_root, skill_installed)


if __name__ == "__main__":
    main()
