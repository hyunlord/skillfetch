---
name: skillfetch-vet
description: Check an agent skill before installing it. Use whenever the user asks to install, add, copy or download a skill (a SKILL.md folder, or a GitHub repo of skills) into .claude/skills or ~/.claude/skills.
---

# Check a skill before installing it

When the user asks you to install a skill, before copying or cloning anything:

1. Call `scan_skill` (skillfetch MCP server) with the skill's GitHub URL
   (`https://github.com/<owner>/<repo>/tree/<ref>/<path>`) or its local folder.
2. Show the user `advice_line` and `license_line` exactly as returned. For CAUTION or
   NOT RECOMMENDED, list each reason with the file, line number and quoted line (at most five).
3. Ask whether to go ahead, and install only after they say yes. On NOT RECOMMENDED, say
   plainly that the scan advises against it.
4. If `scan_skill` returns an error or is not available, say the skill was not checked and ask.

Never run a script from the skill while checking it.
