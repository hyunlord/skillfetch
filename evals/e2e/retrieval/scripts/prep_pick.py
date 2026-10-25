#!/usr/bin/env python3
"""(b) inputs: per gold query, the user's task prompt, the repo, the query Claude sent, and BM25 top-50
(id, title, summary) in rank order. No gold, no expert, no condition. 4 batches -> pick-input/batch_N.md.
Also records the size of the 50 summaries per query (chars/4, the estimate skillfetch uses for token_estimate)."""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
REPO = {"fastapi": "fastapi full-stack template (FastAPI + SQLModel + Postgres backend, React/TanStack frontend)",
        "nextjs": "Next.js with-typescript example (Pages Router)"}


def line(i, c):
    return f"{i}. {c['id']} — {c['title']}: {c['summary']}"


def main():
    qs = [json.loads(l) for l in (R / "retrieval-eval.jsonl").read_text().splitlines()]
    (R / "pick-input").mkdir(exist_ok=True)
    sizes = []
    batches = [qs[i::4] for i in range(4)]
    for n, batch in enumerate(batches, 1):
        parts = []
        for q in batch:
            top = json.loads((R / "top50" / f"{q['qid'].replace('#', '_')}.json").read_text())
            cands = "\n".join(line(i, c) for i, c in enumerate(top, 1))
            sizes.append({"qid": q["qid"], "n": len(top), "chars": len(cands), "tokens_est": len(cands) // 4})
            parts.append(f"## {q['qid']}\n\nRepo: {REPO[q['repo']]}\n\nUser's task:\n> {q['prompt'].strip()}\n\n"
                         f"Query sent to search_skills:\n> {q['query']}\n\nCandidates (search rank order):\n{cands}\n")
        (R / "pick-input" / f"batch_{n}.md").write_text("\n".join(parts))
    (R / "pick-sizes.jsonl").write_text("".join(json.dumps(s) + "\n" for s in sizes))
    t = sorted(s["tokens_est"] for s in sizes)
    print(f"queries {len(t)}; 50-summary block tokens (chars/4): min {t[0]} median {t[len(t)//2]} max {t[-1]}")


if __name__ == "__main__":
    main()
