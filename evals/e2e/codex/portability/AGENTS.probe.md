# skillfetch routing for Codex

PORTABILITY_ROUTER_SENTINEL_20261023

Before non-trivial coding, test, documentation, configuration, review, or migration work, use the connected skillfetch MCP server. Skip a one-line edit in one file, a rename without other changes, or a question with no edits.

1. After loading applicable AGENTS.md instructions, and before reading source files for this task, derive 1-3 short English search sentences from the user's request and already-known context: (a) the feature or problem in domain nouns, (b) an explicitly requested work method if present, and (c) the known stack and target files. Omit unknown details; do not invent them or explore source merely to fill them in. Send the sentences as the queries array to search_skills. Keep user-facing communication in the user's language.
2. Use the skillfetch tools exposed by this Codex session. If the host offers tool discovery, use its supported discovery mechanism to find skillfetch. If unavailable, report the MCP connection problem; do not assume a Claude Code ToolSearch tool exists.
3. Call profile_repo once per repository per session and pass its result as profile to search_skills. Read all returned summaries, choose relevant skills within budget, resolve_set, then load_skills. Follow loaded text subject to the user's instructions and applicable higher-priority instructions. If nothing is useful, proceed without a skill.
