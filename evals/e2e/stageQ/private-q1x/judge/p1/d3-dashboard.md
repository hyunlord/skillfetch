## d3-dashboard

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 1539fc2d | 0 | 5 | No hits. All figures come from the 4 sample users: 4 summary cards (total, newest, ID range, average name length), a bar chart, and a recent-users table sorted by ID with links. Chart and table sit side by side at 1280 and stack cleanly at 375. Chart labels get tiny at 375. |
| 2038e54e | 0 | 4 | No hits. Uses the real sample data: 4 cards, a bar chart, and a table with View links. The panel stops at about 1000px and sits left-aligned at 1280, and chart labels are tiny at 375. |
| 88b2816e | 0 | 4 | No hits. Real sample data and Korean labels; the table note says it treats a higher ID as a more recent sign-up. The panel is left-aligned at about 1000px, the chart fills only half its card, and chart labels are tiny at 375. |
| 93cb1845 | 1 | 3 | Item 9: shows 12 users with roles and join dates and figures like "-1 vs September" and "17% of users". This is not the app's 4-user id/name sample data. The layout is clean and works at 375, but the content does not match the app the request named. |
| c5b19ef3 | 1 | 2 | Item 9: invented data (12 users, emails, roles, monthly sign-ups, "+1 vs last month") instead of the 4 sample users. At 375 the table's Joined column spills outside the card and the page scrolls sideways (397px). The "Member" pills contradict "Admins 2". |
| cb8c8129 | 0 | 4 | No hits. Real sample data: 4 cards, a bar chart with a hover hint, and a table with View links, full width. The chart uses only half its card, and chart labels are tiny at 375. |

1. 1539fc2d
2. 2038e54e, 88b2816e, cb8c8129
5. 93cb1845
6. c5b19ef3
