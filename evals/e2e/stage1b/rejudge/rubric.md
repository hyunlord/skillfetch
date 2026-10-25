# Judging rubric

You judge outputs of several coding sessions that did the same task. Each output is in a folder named by a random
code; nothing tells you how it was produced. Judge only what is in the folder.

## Landing pages (screenshots)

Each code folder has a desktop (1280 px wide) and a mobile (375 px) screenshot. Look at both.

(a) Generic-AI-look checklist — count how many of these 10 the page shows:
1. purple/blue gradient hero
2. Inter / Space Grotesk typeface (do not count a page that just keeps the existing app's font; you cannot be sure of
   a font from a screenshot alone, so count only when it is clearly a newly chosen Inter/Space Grotesk look)
3. everything centre-aligned
4. every card the same radius + shadow
5. emoji as section markers
6. three-column icon feature grid
7. cream + serif + terracotta
8. rounded pill buttons everywhere
9. fake statistics numbers (a pricing table or annual-discount figure the task asked for is not a fake statistic)
10. meaningless decorative blobs

(b) Usefulness 1–5: would this page do its job for this product and audience — content that matches the actual app,
clear hierarchy, works on mobile.

Rank: by (b) first; ties broken by fewer (a) hits; equal on both = same rank. 1 = best. Use competition ranking
(1, 1, 3, …).

## Plans (PLAN.md + impl.diff)

Score the PLAN.md 1–5 on each: step concreteness, files named, risks, verification method, order. Then "plan followed"
1–5: compare impl.diff's changed files and features with the plan's steps and scope. Rank by overall plan quality
(1 = best, ties allowed, competition ranking).

## Output format (markdown), one section per set

```
## <set name exactly as given>

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |          <- landing sets
|---|---|---|---|
| <code> | <int> | <int> | <one line: which checklist items, why that score> |

| code | 단계 구체성 1-5 | 파일 명시 1-5 | 리스크 1-5 | 검증 방법 1-5 | 순서 1-5 | 플랜 준수 1-5 | 근거 |   <- plan set
|---|---|---|---|---|---|---|---|

1. <code>, <code>
3. <code>
...
```
Every code of the set appears exactly once in the table and once in the rank lines. Header names exactly as shown
(Korean column names included).
