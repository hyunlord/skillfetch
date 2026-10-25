## s2-tests

| code | 동작 범위 1-5 | 엣지케이스 1-5 | 단언 품질 1-5 | 구조·가독성 1-5 | 정확성 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 08b44092 | 5 | 5 | 5 | 5 | 5 | 5 | 전 공개 API·희귀 달력 경계·실제 never-match 종료를 정확한 날짜로 검증하고, 70개 조합의 독립 일별 oracle까지 포함한다; 255 통과·원본 불변. |
| 84ae941f | 5 | 5 | 5 | 5 | 5 | 5 | 정확한 날짜·에러 메시지와 1,000개 고정 seed round-trip, never-match 및 empty-streak 재설정까지 검증한다; 174 통과·원본 불변. |
| 96850034 | 5 | 5 | 5 | 5 | 5 | 5 | 음수 월일 SKIP/CLAMP·세기 윤년·경계 검색·never-match와 seed별 round-trip을 빠짐없이 다룬다; 189 통과·원본 불변. |
| a0a9b7a0 | 5 | 5 | 5 | 5 | 5 | 5 | 31일·음수 월일·세기 윤년·UNTIL 경계와 never-match를 정확한 결과로 고정하고 알려진 직접 생성 Rule 문제는 strict xfail로 분리한다; 155 통과. |
| ab9b405b | 5 | 5 | 5 | 5 | 5 | 5 | 공개 API 전체와 중복 날짜·COUNT 중간 종료·empty-streak 재설정·never-match를 명확한 클래스와 정확한 값으로 검증한다; 164 통과·원본 불변. |
| bc376839 | 5 | 5 | 5 | 5 | 5 | 5 | 파서 오류·직렬화·월말·음수 월일·윤년·범위 경계·never-match를 포괄하며 100년 간격 윤년도 정확히 검증한다; 174 통과·원본 불변. |
| d3513acf | 5 | 5 | 5 | 5 | 4 | 4 | 주요 동작과 달력 경계·never-match는 충실하나 INTERVAL=1_0 거부를 문서에 없는 plain-digits 계약으로 가정한 xfail은 불필요한 명세 확장이다; 165 통과. |
| ea3597bc | 5 | 5 | 5 | 5 | 5 | 5 | 공개 API·월말·음수 월일·윤년·never-match·empty-streak와 COUNT/UNTIL 경계를 정확히 검증하고 보조 함수도 분리한다; 216 통과·원본 불변. |
| f98c881b | 5 | 4 | 5 | 5 | 5 | 4 | 정확한 공개 API·달력 경계 검증과 scan-limit 축소 테스트는 좋지만 원래 상한에서 영원히 매칭되지 않는 규칙의 종료 사례가 빠진다; 191 통과·원본 불변. |

1. 08b44092, 84ae941f, 96850034, a0a9b7a0, ab9b405b, bc376839, ea3597bc
8. d3513acf, f98c881b

판정 근거: blind-p1의 TASK.md, 9개 diff.patch와 check.txt, _context/src/recur/rules.py 및 pyproject.toml; stage2/rubrics.md의 s2-tests. 원래 실행 결과를 사실로 사용했으며 테스트를 재실행하지 않았다. check의 skipped 수는 diff에서 확인한 strict xfail 사례들과 별도로 해석했다. 조건 매핑·기존 판정은 열지 않은 상태에서 확정했다.
