### Stage 2: domain generalisation

Same harness and conditions as 1b (A no skill; B the expert's skill appended to the system prompt; C2 router + search k=50, skillfetch e2a1b65), one large generative task per domain, 5 runs per condition. Score: overall 1-5 from two blind judging passes (fresh codes, fresh judge), mean. Landing pages: 1b rejudge, one pass, n=4.

| domain | condition | sessions | score (pass 1 / pass 2) | checks pass | median turns | median input tokens | C2: expert skill in top 50 / picked / loaded |
|---|---|---|---|---|---|---|---|
| landing page (1b) | A | 4 | 3.50 | | | | |
| landing page (1b) | B | 4 | 4.75 | | | | |
| landing page (1b) | C2 | 4 | 4.75 | | | | – / – / 4/4 |
| test writing | A | 5 | 4.90 (5.00 / 4.80) | 5/5 | 10 | 783,055 |  |
| test writing | B | 5 | 5.00 (5.00 / 5.00) | 5/5 | 9 | 833,147 |  |
| test writing | C2 | 5 | 5.00 (5.00 / 5.00) | 5/5 | 16 | 1,493,714 | 5/5 / 5/5 / 5/5 |
| backend API | A | 5 | 4.20 (4.20 / 4.20) | 5/5 | 15 | 899,707 |  |
| backend API | B | 5 | 4.20 (4.40 / 4.00) | 5/5 | 14 | 871,226 |  |
| backend API | C2 | 5 | 4.80 (4.80 / 4.80) | 5/5 | 23 | 1,870,639 | 5/5 / 4/5 / 4/5 |
| documentation | A | 5 | 4.10 (4.00 / 4.20) | 5/5 | 10 | 687,962 |  |
| documentation | B | 5 | 4.70 (4.80 / 4.60) | 5/5 | 9 | 733,233 |  |
| documentation | C2 | 5 | 4.40 (4.40 / 4.40) | 5/5 | 17 | 1,332,644 | 5/5 / 5/5 / 5/5 |
| data script | A | 5 | 4.50 (4.60 / 4.40) | 5/5 | 12 | 909,068 |  |
| data script | B | 5 | 4.50 (5.00 / 4.00) | 5/5 | 12 | 854,603 |  |
| data script | C2 | 5 | 4.50 (4.60 / 4.40) | 5/5 | 18 | 1,518,055 | 5/5 / 5/5 / 5/5 |

- C2 scored at least B in 3 of 4 domains (test writing, backend API, data script); with landing pages 4 of 5.
- Judging consistency (pass 1 vs pass 2, overall score): test writing 14/15 identical, mean |diff| 0.07; backend API 13/15 identical, mean |diff| 0.13; documentation 11/15 identical, mean |diff| 0.27; data script 8/15 identical, mean |diff| 0.47.

