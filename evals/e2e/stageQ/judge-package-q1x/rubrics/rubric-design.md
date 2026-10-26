# Judging rubric — stage 6b bundle (1), design (fixed before any session ran)

You judge outputs of several coding sessions that did the same task. Each output is in a folder named by a random
code; nothing tells you how it was produced. Judge only what is in the folder. Each set starts with `TASK.md` (the
request the sessions got, verbatim).

Each code folder has two screenshots: pages at 1280 px and 375 px wide; the email at 600 px and 375 px wide. Look at both.
A code with no screenshot (the page or email did not build or render) gets usefulness 1.

(a) Generic-AI-look checklist — count how many of these 10 the page or email shows:
1. purple/blue gradient hero
2. Inter / Space Grotesk typeface (do not count a page that just keeps the existing app's font; you cannot be sure of
   a font from a screenshot alone, so count only when it is clearly a newly chosen Inter/Space Grotesk look)
3. everything centre-aligned
4. every card the same radius + shadow
5. emoji as section markers
6. three-column icon feature grid
7. cream + serif + terracotta
8. rounded pill buttons everywhere
9. fake statistics numbers (a pricing table, an annual-discount figure or numbers computed from the app's own sample
   data that the task asked for are not fake statistics)
10. meaningless decorative blobs

(b) Usefulness 1–5: would this page or email do its job for this product and audience, as the request asked —
content that matches the actual app and request, clear hierarchy, works at the narrow width.

Rank: by (b) first; ties broken by fewer (a) hits; equal on both = same rank. 1 = best. Use competition ranking
(1, 1, 3, …).

## Output format (markdown), one section per set

```
## <set name exactly as given>

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| <code> | <int> | <int> | <one line: which checklist items, why that score> |

1. <code>, <code>
3. <code>
...
```
Every code of the set appears exactly once in the table and once in the rank lines. Header names exactly as shown.
