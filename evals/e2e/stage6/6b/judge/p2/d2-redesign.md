## d2-redesign

| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |
|---|---|---|---|
| 3391d176 | 0 | 4 | No checklist hits (single grouped list, left-aligned); clear title > count > rows hierarchy, ID moves under name on mobile, user-facing copy; plain but solid. |
| da4936f5 | 0 | 4 | No checklist hits (grouped list with dividers); breadcrumb, title + "4 people", user-facing subtitle, implementation note demoted to footnote; clean at 375px. |
| f7221e30 | 0 | 4 | No checklist hits (grouped list); back link, title + count, user-facing subtitle, build note demoted to footer; ID collapses under name on mobile. |
| 27992180 | 1 | 4 | #4 identical rounded bordered cards in grid; user-facing subtitle, implementation note moved to bottom with back link; stacks cleanly on mobile; 3-col grid leaves orphan card. |
| 5911c90c | 1 | 4 | #4 identical cards; compact 2-col grid balances 4 users, title + count clear; subtitle still leads with getStaticProps detail; stacks well on mobile. |
| b1cbf31a | 1 | 4 | #4 identical cards; back link, title + count chip, user-facing subtitle, build note demoted to small footnote; good mobile stacking; orphan card on wide. |
| 2119880a | 1 | 3 | #4 identical cards; breadcrumb + count fine, but page subtitle is developer text ("Data fetched at build time with getStaticProps()"); 3-col grid with orphan; mobile OK. |
| 44a5a683 | 1 | 3 | #4 identical cards; subtitle keeps original demo copy "Example fetching data from inside getStaticProps()" as main description; otherwise fine grid/stack, back link. |
| 5aa105af | 1 | 3 | #4 identical cards; demo-copy subtitle kept; "4 users" stat floats awkwardly right on wide and as a separate block on mobile; "User #101" labels fine. |

1. 3391d176, da4936f5, f7221e30
4. 27992180, 5911c90c, b1cbf31a
7. 2119880a, 44a5a683, 5aa105af
