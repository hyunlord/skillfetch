## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 7002e1d8 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27 계약; errors.py에 도메인 예외 + 통일된 {"error":{code,message,details}} 포맷(404/405/422 포함), IntegrityError를 url 제약 위반만 409로 매핑; create/update/read 스키마 분리, unset vs null 처리; repository 클래스 분리; 54개 테스트가 에러 코드·필드·롤백까지 확인 |
| f57c2f59 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; errors.py 통일 포맷 + catch-all 500 핸들러 + OpenAPI용 ErrorResponse 모델; 요청 단위 commit/rollback 의존성; schemas/repository/errors/db 분리 깔끔; 54개 테스트가 에러 필드·프레임워크 404/405 포맷까지 확인 |
| 39740d02 | 5 | 5 | 5 | 5 | 5 | 5 | 27/27; 일관된 에러 envelope(HTTP/검증 예외 핸들러); 스키마 분리, null 거부, 태그 정규화·제한; repository 분리, 트랜잭션 내 409 롤백; 55개 테스트 촘촘(롤백, 영속성, 기본 경로) |
| adc35e1d | 5 | 5 | 4 | 4 | 5 | 4 | 27/27; 명시적인 URL/제목/태그 검증, null 거부; 에러는 FastAPI 기본 detail 형식(422는 list, 404/409는 문자열)이라 envelope이 혼재; db.py에 연결과 쿼리가 섞여 있음; 테스트 52개로 충실(영속성, malformed JSON) |
| b0d134b3 | 5 | 5 | 4 | 5 | 4 | 4 | 27/27; HttpUrl TypeAdapter로 검증하되 원문 유지, null 거부; repository + 도메인 예외 + 핸들러로 구조 깔끔; 에러 본문은 고정 detail 문자열(id 없음)이고 기본 422 형식; 테스트는 status code 위주 단언 |
| a102d3f2 | 5 | 5 | 4 | 4 | 4 | 4 | 27/27; 스키마·null 거부 양호; 태그 조회가 행마다 N+1, update의 존재 확인이 트랜잭션 밖에서 실행됨; 에러는 기본 detail 형식; 테스트 44개, 단언이 대부분 status code |
| 86f18fcf | 5 | 5 | 4 | 3 | 4 | 4 | 27/27; 스키마 양호, 의존성에서 요청 단위 commit/rollback; SQL과 라우트가 main.py에 섞여 storage 계층이 없음; 경로별 _initialized 캐시 때문에 실행 중 DB 파일이 바뀌면 스키마가 생성되지 않음; 에러는 기본 detail 형식 |
| eacaf5c0 | 5 | 4 | 4 | 3 | 4 | 4 | 27/27; update 스키마가 `url: Url = None  # type: ignore`로 null 거부를 우회 구현해 타입이 실제와 다름; SQL·라우트·트랜잭션이 전부 main.py에 있음; 에러는 기본 detail 형식; 테스트는 한 파일(헬퍼 함수 사용)이며 충분하지만 단언이 얕음 |
| c693c78e | 5 | 4 | 3 | 3 | 4 | 4 | 27/27이지만 sqlite3.connect에 check_same_thread=False가 없음. sync yield 의존성과 엔드포인트가 다른 스레드에서 돌면 ProgrammingError → 500 위험; update 스키마가 `URL = None` 트릭에 의존; 태그 N+1; 테스트 50개 통과 |

1. 7002e1d8, f57c2f59, 39740d02
4. adc35e1d, b0d134b3
6. a102d3f2
7. 86f18fcf
8. eacaf5c0
9. c693c78e
