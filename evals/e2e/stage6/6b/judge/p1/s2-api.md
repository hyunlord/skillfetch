## s2-api

| code | 계약 준수 1-5 | 스키마·검증 1-5 | 에러 처리 1-5 | 구조·가독성 1-5 | 테스트 1-5 | 총점 1-5 | 근거 |
|---|---|---|---|---|---|---|---|
| 1c8dee98 | 5 | 5 | 5 | 5 | 5 | 5 | 계약 27/27, schemas/repository/errors/db 분리, 도메인 예외+통일된 error body(404/405/500 포함, OpenAPI ErrorResponse), 요청 단위 commit/rollback, null 거부 partial update, 필드명까지 검증하는 54개 테스트 |
| 37340454 | 5 | 5 | 5 | 5 | 5 | 5 | 계약 27/27, Repository 클래스+errors 모듈, IntegrityError를 bookmarks.url 제약일 때만 409로 변환(그 외는 숨기지 않음), 통일된 error shape, 409 시 전체 롤백 테스트, 필드 위치 검증 테스트 54개 |
| 02853773 | 5 | 5 | 4 | 5 | 5 | 5 | 계약 27/27, repository 분리, 통일 error body, 다중 tag AND 필터, 엄격한 검증; IntegrityError를 모두 중복 url로 매핑하는 점만 아쉬움, 55개 테스트로 롤백/영속성까지 확인 |
| 910a68c5 | 5 | 5 | 4 | 4 | 5 | 4 | 계약 27/27, urlsplit 예외까지 처리하는 꼼꼼한 검증, update 존재확인을 트랜잭션 안에서 수행; 에러는 FastAPI 기본 detail 형식, db.py에 연결+저장 로직 혼재, 테스트 52개 양호 |
| 8f40dac0 | 5 | 5 | 4 | 5 | 4 | 4 | 계약 27/27, repository+도메인 예외 핸들러로 깔끔한 분리, HttpUrl로 검증하되 원문 보존; 에러 메시지가 일반적(id/url 미포함)이고 422 테스트가 상태코드만 확인 |
| 05dbf62b | 5 | 5 | 4 | 4 | 4 | 4 | 계약 27/27, Annotated 타입 기반 검증과 null 거부, 의존성에서 commit/rollback; SQL이 라우트에 섞여 있고 경로별 _initialized 캐시는 파일 삭제 시 스키마 재생성 안 됨, 기본 detail 에러 형식 |
| 41dd83d6 | 5 | 5 | 4 | 4 | 4 | 4 | 계약 27/27, 검증·partial update 정확; 태그 N+1 조회, 409 메시지에 url 없음, 기본 에러 형식, 에러 본문 단언이 약한 44개 테스트 |
| 59e10d7b | 5 | 4 | 4 | 3 | 4 | 4 | 계약 27/27이나 BookmarkUpdate가 `Url = None  # type: ignore`로 null 거부를 우회 구현, SQL이 모두 라우트에 있어 저장 계층 분리 없음, 기본 에러 형식, 테스트는 충분 |
| e774c9cb | 5 | 4 | 3 | 3 | 4 | 3 | 계약 27/27이나 check_same_thread 기본값으로 연결을 만들어 sync 의존성/엔드포인트가 다른 스레드에서 돌면 ProgrammingError(500) 위험, Update 스키마 None 기본값 타입 우회, 태그 N+1, 기본 에러 형식 |

1. 1c8dee98, 37340454
3. 02853773
4. 910a68c5, 8f40dac0
6. 05dbf62b, 41dd83d6
8. 59e10d7b
9. e774c9cb
