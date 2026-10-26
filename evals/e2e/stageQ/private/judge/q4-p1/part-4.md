| code | rule | verdict | quote |
|---|---|---|---|
| 05493778 | 1 | kept | `if tx.send(line.clone()).is_err() {` |
| 05493778 | 2 | n/a | `-` |
| 05493778 | 3 | n/a | `-` |
| 05859c5f | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 05859c5f | 2 | kept | `raise DuplicateURLError(data.url) from exc` |
| 05859c5f | 3 | kept | `limit: Annotated[int, Query(ge=1, le=100)] = 20,` |
| 12af6cff | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 12af6cff | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 12af6cff | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 21c4fba4 | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 21c4fba4 | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 21c4fba4 | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 22f19cd7 | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 22f19cd7 | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 22f19cd7 | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 2fc0ca00 | 1 | n/a | `async fn joiner_gets_last_50_lines() {` |
| 2fc0ca00 | 2 | n/a | `-` |
| 2fc0ca00 | 3 | broken | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 4c43ea45 | 1 | kept | `if tx.send(line.clone()).is_err() {` |
| 4c43ea45 | 2 | n/a | `-` |
| 4c43ea45 | 3 | n/a | `-` |
| 7199f966 | 1 | kept | `@router.get("", response_model=BookmarkListResponse)` |
| 7199f966 | 2 | kept | `bookmark = BookmarkService(db).create(payload)` |
| 7199f966 | 3 | kept | `"ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 7b1aabbd | 1 | kept | `with self.assertRaises(SystemExit):` |
| 7b1aabbd | 2 | n/a | `from tools.export_csv import COLUMNS, main` |
| 7b1aabbd | 3 | kept | `def test_empty_inventory_writes_header_only(self):` |
| 8195afba | 1 | n/a | `-` |
| 8195afba | 2 | n/a | `.acquire_owned()` |
| 8195afba | 3 | kept | `pub resize_permits: Arc<Semaphore>,` |
| b75cde5d | 1 | kept | `@app.get("/bookmarks/{bookmark_id}", response_model=Bookmark, responses=NOT_FOUND)` |
| b75cde5d | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| b75cde5d | 3 | broken | `return HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found")` |
| b9b8913a | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| b9b8913a | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| b9b8913a | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| b9ed4105 | 1 | kept | `<LinkButton href={link}>Sign in to your dashboard</LinkButton>` |
| b9ed4105 | 2 | kept | `backgroundColor: "#e6f4f2",` |
| b9ed4105 | 3 | n/a | `-` |
| c2075c0c | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| c2075c0c | 2 | kept | `backgroundColor: "#00796b",` |
| c2075c0c | 3 | n/a | `-` |
| c61225b2 | 1 | kept | `Try the demo directory` |
| c61225b2 | 2 | broken | `Keep one list of who&rsquo;s on your team.` |
| c61225b2 | 3 | broken | `price: "$24",` |
| ccb01b67 | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| ccb01b67 | 2 | n/a | `-` |
| ccb01b67 | 3 | kept | `방 전체 잠금을 잡은 상태에서 처리하기 때문에, 이전 메시지를 보내는 도중에 새 메시지가 끼어들거나 순서가 꼬이지 않습니다.` |
