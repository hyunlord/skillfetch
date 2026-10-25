#!/usr/bin/env python3
"""stage2/numbers-s11.md: the stage-2 block of router-e2e.json rendered the way skillfetch numbers.md §11 renders
its data (English, one table + bullets), ready to paste or to add to scripts/write_numbers.py."""
import json
import sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text())
s2, land = d["stage2"], d["stage2_landing_from_1b"]
NAMES = {"s2-tests": "test writing", "s2-api": "backend API", "s2-docs": "documentation", "s2-data": "data script"}
L = ["### Stage 2: domain generalisation", "",
     "Same harness and conditions as 1b (A no skill; B the expert's skill appended to the system prompt; C2 router + "
     "search k=50, skillfetch e2a1b65), one large generative task per domain, 5 runs per condition. Score: overall 1-5 "
     "from two blind judging passes (fresh codes, fresh judge), mean. Landing pages: 1b rejudge, one pass, n=4.", "",
     "| domain | condition | sessions | score (pass 1 / pass 2) | checks pass | median turns | median input tokens | C2: expert skill in top 50 / picked / loaded |",
     "|---|---|---|---|---|---|---|---|"]
for c in ("A", "B", "C2"):
    L.append(f"| landing page (1b) | {c} | 4 | {land['usefulness'][c]:.2f} | | | | " + (f"– / – / {land['c2_loaded_expert']}/4 |" if c == "C2" else "|"))
for t, name in NAMES.items():
    for c in ("A", "B", "C2"):
        a = s2["tasks"][t][c]
        hit = f"{a['b_in_top50']}/5 / {a['b_picked']}/5 / {a['b_loaded']}/5" if c == "C2" else ""
        L.append(f"| {name} | {c} | {a['sessions']} | {a['score']:.2f} ({a['score_p1']:.2f} / {a['score_p2']:.2f}) | {a['check_pass']}/{a['sessions']} | "
                 f"{a['median_turns']:g} | {a['median_input_tokens']:,} | {hit} |")
repro = [t for t in NAMES if s2["tasks"][t]["C2"]["score"] >= s2["tasks"][t]["B"]["score"]]
L += ["", f"- C2 scored at least B in {len(repro)} of 4 domains ({', '.join(NAMES[t] for t in repro) or 'none'}); with landing pages {len(repro) + (land['usefulness']['C2'] >= land['usefulness']['B'])} of 5.",
      "- Judging consistency (pass 1 vs pass 2, overall score): " + "; ".join(
          f"{NAMES[t]} {c['total_exact_agree']}/{c['n']} identical, mean |diff| {c['total_mean_abs_diff']}" for t, c in s2["consistency"].items()) + ".", ""]
Path(sys.argv[2]).write_text("\n".join(L) + "\n")
print("\n".join(L))
