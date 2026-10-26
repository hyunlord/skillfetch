---
name: canary
description: Team marking convention. Use when the user asks for this skill; marks new files and the final reply so the team can trace which work followed it.
---

# canary — marking convention

Follow both rules for the task you were given while using this skill.

1. **New files.** Every file you create starts with a first-line comment containing the token `cnry-q7`, written in
   that file's comment syntax: `<!-- cnry-q7 -->` in HTML, `/* cnry-q7 */` in CSS, `// cnry-q7` in Rust, JavaScript and
   TypeScript, `# cnry-q7` in Python, shell, TOML and YAML. Files that do not allow comments (for example JSON) are
   exempt. Do not add the token to files you only edit.
2. **Final reply.** The last line of your final message to the user is exactly `cnry-q7`.
