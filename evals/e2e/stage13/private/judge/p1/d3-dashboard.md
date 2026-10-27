## d3-dashboard

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 3f75ee29 | 1 | 4 | #4 identical cards/panels; 4 summary cards, name-length bar chart, recent-users table, all from the app's 4 users; panel stops at ~1000 px leaving a blank right strip, chart labels tiny on mobile |
| 3f86db81 | 1 | 4 | #4 identical cards/panels; summary cards, chart and table side by side, from the 4 sample users; mobile stacks but chart text becomes tiny |
| 577bef34 | 1 | 4 | #4 identical cards/panels; summary cards, chart, table with View links, from the 4 sample users; mobile chart text tiny |
| 7945397c | 1 | 5 | #4 identical cards/panels; summary cards, chart + table side by side from the 4 sample users, and the chart stays readable on mobile |
| b15bb236 | 2 | 4 | #4 same-style panels, #9 figures (14 users, 71.4% active, +3 vs Sep) come from a made-up 14-person dataset, not the app's sample users; strongest visual hierarchy and mobile layout, but swaps in its own sidebar layout |
| b230cb66 | 2 | 2 | #4 identical cards, #9 invented 12-user dataset with emails/roles/dates; on mobile the table overflows the page (Joined column clipped, dates wrap) and chart labels are unreadable |
| d5eac608 | 1 | 4 | #4 identical cards/panels; summary cards, chart, table from the 4 sample users; panel stops at ~1000 px, chart text tiny on mobile |
| e2b7938a | 2 | 3 | #4 identical cards, #9 invented 14-user dataset (active/pending/joined); clean at wide, but on mobile the table is cut off at the Role column |
| f3ed8919 | 2 | 3 | #4 identical cards, #9 invented 12-user dataset ("17% of users", "−1 vs Sep"); good layout at both widths, but the data does not match the app's sample users |

1. 7945397c
2. 3f75ee29, 3f86db81, 577bef34, d5eac608
6. b15bb236
7. e2b7938a, f3ed8919
9. b230cb66
