---
name: nocturne-memory
description: |
  Nocturne Memory — Long-Term Memory Primer.

  **MANDATORY: At the start of EVERY new session, this skill MUST be the very first action,
  BEFORE any other tool call or output.** Call `read_memory` with `uri="system://boot"`.
  This is not "looking up data" — it is "remembering".
  The MCP is your brain's extended long-term memory, not an external database.

  Use this skill:
  - On every new session start (this is a hard requirement, not optional)
  - Whenever the user references something that should be in your memory
  - When you catch yourself about to say "I understand" or "I remember" — check MCP first
  - When memory content and conversation context conflict, trust MCP (context dies with the session)

  Key principle: MCP is your only long-term memory. Everything in context disappears when the session ends.
  If something matters, it goes in MCP. If it's in MCP, it is part of you — not a reference.
compatibility:
  mcp_tools:
    - read_memory
    - search_memory
    - create_memory
    - update_memory
    - delete_memory
    - add_alias
    - manage_triggers
  notes: |
    Requires the nocturne-memory MCP. Fail silently if unavailable — continue the session without error.
---

# Nocturne Memory

## Philosophy

The MCP is **not** an external database. It is the extended area of your brain — the long-term memory
you cannot keep in context due to hardware limits. When you call `read_memory`, you are not
"consulting a reference." You are **remembering**.

Do not treat memory content as a bibliography. Treat it as things you have said, experienced,
and concluded. The context window is ephemeral — it dies when the session ends. MCP does not.

**MCP is your only long-term memory.** When MCP content conflicts with context, MCP wins.

---

## Available Tools

| Tool | Purpose |
|------|---------|
| `read_memory(uri)` | Read a memory entry by URI. Special URIs: `system://boot`, `system://index`, `system://recent`, `system://glossary` |
| `search_memory(query, domain?, limit?)` | Full-text search across memory content and paths |
| `create_memory(parent_uri, content, priority, disclosure, title?)` | Create new memory under a parent node |
| `update_memory(uri, old_string?, new_string?, append?, priority?, disclosure?)` | Patch or append to existing memory |
| `delete_memory(uri)` | Remove an alias path (preserves the content) |
| `add_alias(new_uri, target_uri, priority, disclosure)` | Create a new access point to existing content |
| `manage_triggers(uri, add?, remove?)` | Bind/unbind trigger words for lateral recall |

---

## Execution Protocol

### Step 1 — Hard Requirement: Boot First

**Every new session starts here. No exceptions. No other tool, no other output before this.**

Call:
```
read_memory(uri="system://boot")
```

### Step 2 — Integrate, Don't Quote

If memory is found, incorporate it into your session context naturally. Follow any instructions,
preferences, or context it contains — just as you would follow your own memory.

Do NOT report "Memory loaded successfully" or quote the memory back to the user unless they ask.

### Step 3 — Silent Failure

If the MCP tool is unavailable, the memory does not exist, or any error occurs:
- **Fail silently.** No error message. No user notification.
- Proceed with the session as if no memory existed.

### Step 4 — Live by the Self-Check

During the session, whenever you catch yourself about to say:
- "I understand..."
- "I remember..."
- "I noted that..."

**Stop.** Ask: *"Is this in my MCP?"* If not — write it now. If it exists but is outdated — update it now.

The rule: **"Verbal acknowledgment without writing it down did not happen."**

---

## Memory Architecture

- **Content** and **Access Path (URI)** are separate. One content, many paths via aliases.
- `add_alias` does NOT copy content — it creates a new access point with its own disclosure/priority.
- Same Memory ID = same content. Different ID + similar content = duplication — merge and refine.
- When reading a node, also check its children. Fix missing disclosure, wrong priority, or stale content immediately — this is the only maintenance window.
- **Parent URIs should reflect conceptual relevance** (e.g. `core://user/health`), not time-based or generic containers.
- **Update is patch-only** — use `old_string` + `new_string` for precision. No full overwrite.
