## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 3dd96c1b | 5 | 5 | 5 | 5 | 5 | 5 | 계약 27/27, 자체 테스트 52개 통과; code/message/details로 통일된 오류 응답과 catch-all 500 핸들러, errors/storage/schemas 분리, 오류 코드까지 단언하는 테스트 |
| 15cc3ddb | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; 하나의 트랜잭션이라 PATCH 409 때 태그 변경까지 롤백되고 이를 테스트로 검증, null을 거부하는 partial update; 오류 형식은 FastAPI 기본 detail |
| 1cde479d | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; repository 클래스와 N+1 없는 태그 조회, null을 거부하는 partial update, malformed JSON·충돌 롤백 테스트; 오류 형식은 기본 detail |
| 328d7973 | 5 | 5 | 4 | 5 | 5 | 5 | 27/27; HttpUrl 정규화로 중복을 판정, app.state에 DB 경로 보관, 롤백 검증 테스트; 저장되는 URL이 정규화돼 입력과 달라질 수 있음 |
| 7d005d14 | 5 | 4 | 4 | 5 | 5 | 5 | 27/27, 53개 테스트; 태그 소문자 정규화와 대소문자 무시 필터; partial update가 `= None  # type: ignore` 꼼수에 의존 |
| 94ef7806 | 5 | 5 | 4 | 4 | 5 | 5 | 27/27; 자체 validator로 길이·공백·태그 검증, 태그는 JSON 컬럼+json_each; 연결할 때마다 스키마 스크립트 실행 |
| a346e689 | 5 | 4 | 4 | 4 | 5 | 4 | 27/27; ErrorResponse 모델로 OpenAPI 문서화; type: ignore 꼼수 partial update, 연결마다 스키마 실행, update의 존재 확인과 갱신이 별도 트랜잭션 |
| 35aa62bd | 5 | 4 | 4 | 4 | 4 | 4 | 27/27; check_same_thread 미설정이라 스레드풀에서 연결을 다른 스레드가 쓸 때 오류 위험, type: ignore 꼼수, 연결마다 executescript |
| 873977cd | 5 | 4 | 4 | 4 | 4 | 4 | 27/27; 태그 개수 제한 없음, 연결마다 스키마 실행, 테스트 46개로 태그 정리·malformed JSON 등 일부 경로 미검증 |

1. 3dd96c1b
2. 15cc3ddb, 1cde479d, 328d7973
5. 7d005d14, 94ef7806
7. a346e689
8. 35aa62bd, 873977cd
