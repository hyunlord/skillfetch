## d3-dashboard

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 4706d827 | 1 | 4 | #4 (uniform bordered cards); Korean UI matching the request, 4 summary cards from the real 4 users, name-length bar chart, recent-users table with stated "higher ID = newer" assumption; stacks on mobile, chart labels tiny at 375 px |
| 0d21fbd2 | 1 | 4 | #4; summary cards, name-length bar chart, recent table with View links, all from the real sample data; stacks cleanly on mobile, chart text tiny at narrow width |
| be9f997f | 2 | 3 | #4, #9 (12 invented users with roles/join dates, "-1 vs September", "17% of users" not from the app's sample data); looks like a real admin dashboard and is responsive, but the content does not match the app's actual 4-user id/name data |
| 2a091586 | 1 | 4 | #4; summary cards with sub-labels, chart and table side by side on wide, stacked on mobile, all derived from real sample data, names link to detail; best use of width among the real-data versions |
| 9a27b717 | 1 | 4 | #4; summary cards (incl. longest name), name-length chart, recent table with profile links, real data; panel stops at ~1000 px leaving blank right side, fine on mobile |
| f73be5ab | 2 | 2 | #4, #9 (12 invented users/emails/signup months not in the app's data); at 375 px the recent-users table overflows the card and the date column spills past the panel |

1. 4706d827, 0d21fbd2, 2a091586, 9a27b717
5. be9f997f
6. f73be5ab
