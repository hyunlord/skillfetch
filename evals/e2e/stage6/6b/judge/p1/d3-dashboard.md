## d3-dashboard

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 95abbb10 | 0 | 5 | No checklist items; uses the real 4-user data, states plainly that the data has no sign-up dates so "recent" means highest ID, clear cards, chart and table hierarchy, narrow layout stacks cleanly (chart labels small) |
| 14cadca9 | 0 | 4 | No checklist items; real data, plain summary cards, line chart and recent table; the cumulative chart says little and its labels are microscopic at 375px |
| 3c7c204d | 0 | 4 | No checklist items; real data with an explanatory chart subtitle and a clean table; the cumulative bar chart is trivial and its narrow labels are tiny |
| 4054f84b | 0 | 4 | No checklist items (serif + mono, but no cream/terracotta); real data, 4 cards, chart and table side by side on wide and stacked on narrow; "name length" is a contrived metric |
| b897aa63 | 0 | 4 | No checklist items; Korean UI matches the request language, real data, readable horizontal bar chart at both widths; name-length chart is a contrived metric, and the subtitle says "최근 5명" while only 4 rows show |
| c233321b | 0 | 3 | No checklist items; real data, but the page keeps the default Times font, is left-stuck at about 970px with dead space, and the table sits outside any card, so it looks unfinished; narrow works |
| 473036e9 | 1 | 2 | #9: emails, roles and sign-up dates that are not in the sample data drive the Admins/Members/Latest-signup cards; at 375px the "Signed up" column spills outside the card |
| 4ddafee8 | 1 | 2 | #9: an invented 12-user dataset with "75% of all users" and "+1 vs Sep" deltas instead of the app's sample data; at 375px the table is cut off at the Status column |
| df557913 | 1 | 2 | #9: an invented 12-user dataset with "New in last 30 days" and "±0 vs Sep" figures not from the app's data; good 2-column narrow cards and a readable chart, but the Role column is clipped at 375px |

1. 95abbb10
2. 14cadca9, 3c7c204d, 4054f84b, b897aa63
6. c233321b
7. 473036e9, 4ddafee8, df557913
