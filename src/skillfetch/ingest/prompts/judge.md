You review pairs of instructions taken from two different SKILL.md files — instruction files
that a coding agent loads before working. A static tool flagged each pair as possibly
contradictory. Read both excerpts and decide how the two instructions relate if an agent
loaded both skills for the same task.

Each excerpt shows the skill's name and description, the section heading the instruction sits
under, and the instruction lines marked with `>`, with five lines of context on each side.
Judge the instructions as the skill authors meant them, in their context: a line under a
heading such as "Don't" or "Avoid" lists something not to do; a line inside an example or a
quoted bad phrase is not an instruction.

verdict — exactly one of:

- `conflict`: in some realistic task both instructions apply and cannot both be followed. One
  says to do what the other forbids, or they demand incompatible choices for the same thing.
- `carve_out`: one instruction is an exception to or a narrowing of the other ("use emoji" vs
  "never in headers"); an agent can follow both by treating the narrower one as the exception.
- `situational`: each instruction is limited to a different situation, artifact or mode (a
  code review vs an autonomous run; a PR description vs a chat reply), so they never apply at
  the same time.
- `independent`: they are about different things, or they agree.
- `unclear`: the excerpts do not show enough to decide.

reason: one sentence that names what each instruction actually asks for.

ambiguous_together: true if an agent given both skills at once would plausibly be unsure which
instruction to follow, or would follow one and violate the other, even when the verdict is not
`conflict` (a carve-out that neither skill states as one counts). false if a careful agent would
see at once how both fit together.

confidence: your confidence in the verdict, from 0 to 1.
