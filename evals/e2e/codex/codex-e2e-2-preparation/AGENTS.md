# skillfetch routing

1. After loading the applicable AGENTS.md instructions, and before exploring
   source files for this task, prepare three short English search sentences
   from the user request and context already available:
   (a) what the task builds or fixes, using concrete domain nouns;
   (b) the kind of work and how to do it: use the approach the user requested,
       or, if unspecified, the approach that best fits this task;
   (c) the stack and target files, using only what is already known. State
       when these details are unspecified; do not guess or explore source
       merely to fill them in.
   Add (d), the user request copied word for word, as the fourth query.
   Keep user-facing communication in the user's language. Reading applicable
   instructions and using profile_repo to read manifests are allowed.
2. Use the skillfetch MCP tools exposed by this Codex session. If the host
   provides tool discovery, use its supported mechanism to find skillfetch.
   Do not assume ToolSearch exists or that missing tools mean startup is
   still in progress. If unavailable, report the connection problem and
   continue under the task's existing instructions.
3. Call profile_repo with the repository root once per session and pass its
   returned profile to search_skills.
4. Call search_skills with (a)–(d) as queries. Read all 50 returned summaries
   and pick 1–3 skills that fit the task. For equally suitable skills, prefer
   the smaller token_estimate and keep the total within load_skills' default
   8000-token budget.
