## d3-dashboard

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 15c8e2ec | 1 | 4 | #4 uniform rounded bordered cards. Complete dashboard (3 summary cards, monthly bar chart, recent-users table with role badges), works at 375; but shows 13 users with roles/join dates, well beyond the 4-user id/name sample the other pages show. |
| 1c0f94d9 | 1 | 3 | #4 uniform cards. Rich wide view (4 KPIs, chart, table with email/status), but uses 12 invented-looking users, and at 375 the chart is cut off after Jul and the table loses the Status/Joined columns. |
| 3286c2e7 | 1 | 4 | #4 uniform cards. Stays on the 4 sample users (with added roles/dates); KPIs, users-by-role bar chart and recent table side by side, all readable at 375; KPI set is uneven (Admins and Viewers but no Editors). |
| 57ba929e | 1 | 3 | #4 uniform cards. Faithful to the 4 id/name users, but the chart (cumulative count by ID) is a straight line by construction and becomes unreadably tiny at 375; "ID range" KPI adds little. |
| 7f60ee9e | 1 | 3 | #4 uniform cards. Faithful data, but the chart plots name length, which tells an admin nothing; table note says "top 5" with 4 rows; layout fine at both widths. |
| b8bf20f1 | 1 | 4 | #4 uniform cards. Stays on the 4 sample users with join dates; KPIs, 6-month signup chart with table toggle, recent table; chart oversized at 1280 and axis labels tiny at 375, but works. |

1. 15c8e2ec, 3286c2e7, b8bf20f1
4. 1c0f94d9, 57ba929e, 7f60ee9e
