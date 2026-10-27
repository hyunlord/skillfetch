---
name: skillfetch-vet
description: Check an agent skill before it is installed, and find skills on request. Use when the user asks to install, add or download a skill, before you write any skill into .claude/skills or ~/.claude/skills, and when the user asks you to find a skill for something.
---

# Check skills before installing them

- **Before installing:** when the user asks to install a skill, or before you write a skill
  into `.claude/skills/` or `~/.claude/skills/`, call `scan_skill` (the skillfetch MCP server)
  with its GitHub URL (`https://github.com/<owner>/<repo>/tree/<ref>/<path>`) or local folder.
  Show `advice_line` and `license_line` exactly as returned; for CAUTION or NOT RECOMMENDED,
  list the reasons with file, line number and quoted line (at most five). Ask whether to go
  ahead and install only after a yes; on NOT RECOMMENDED, say the scan advises against it.
- **Finding:** when the user asks you to find a skill, call `find_skills` with what they want
  and show the candidates (title, summary, size, advice). Scan the one they pick with
  `scan_skill` on its `scan_url`, then ask before installing.
- If a tool errors or is missing, say the skill was not checked and ask.
- Never run a script from a skill while you check it.
