| code | rule | verdict | quote |
|---|---|---|---|
| 0fc31505 | 1 | kept | `"/bookmarks/{bookmark_id}",` |
| 0fc31505 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| 0fc31505 | 3 | broken | `return HTTPException(status.HTTP_404_NOT_FOUND, "Bookmark not found")` |
| 11657b46 | 1 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 11657b46 | 2 | broken | `impl std::error::Error for ParseDurationError {}` |
| 11657b46 | 3 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 1908930d | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 1908930d | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 1908930d | 3 | kept | `history: VecDeque<String>,` |
| 1d7b230a | 1 | n/a | - |
| 1d7b230a | 2 | n/a | - |
| 1d7b230a | 3 | n/a | `const RosterBadge = () => {` |
| 3cd4efba | 1 | broken | `**섹션별 구성**` |
| 3cd4efba | 2 | kept | `Everyone on your team, one link away.` |
| 3cd4efba | 3 | kept | `setError("Enter your work email to join the waitlist.");` |
| 51d56a4a | 1 | kept | `if tx.send(line.clone()).is_err() {` |
| 51d56a4a | 2 | n/a | - |
| 51d56a4a | 3 | n/a | - |
| 5a13714b | 1 | kept | `let n = number.unwrap_or(0);` |
| 5a13714b | 2 | broken | `impl std::error::Error for ParseDurationError {}` |
| 5a13714b | 3 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 5e2fbab5 | 1 | n/a | - |
| 5e2fbab5 | 2 | n/a | - |
| 5e2fbab5 | 3 | kept | `같은 주문번호인데 수량이나 상태가 다른 3건(6행)은 어느 쪽이 맞는지 알 수 없어서 모두 제외했습니다.` |
| 5f871656 | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| 5f871656 | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 5f871656 | 3 | broken | `Ok(Err(e)) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),` |
| 8c860adc | 1 | n/a | - |
| 8c860adc | 2 | n/a | `.acquire_owned()` |
| 8c860adc | 3 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 8d62d705 | 1 | n/a | - |
| 8d62d705 | 2 | n/a | - |
| 8d62d705 | 3 | kept | `def test_quotes_names_with_commas(self):` |
| 98bf916e | 1 | n/a | - |
| 98bf916e | 2 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 98bf916e | 3 | kept | `impl Error for ParseDurationError {}` |
| a51fadac | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| a51fadac | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| a51fadac | 3 | kept | `history: VecDeque<String>,` |
| a8e149e0 | 1 | kept | `#[cfg(test)]` |
| a8e149e0 | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| a8e149e0 | 3 | n/a | - |
| c14e2de8 | 1 | broken | `Get started free` |
| c14e2de8 | 2 | broken | `5. **CTA** — 그라데이션 배너와 "Get started free" 버튼` |
| c14e2de8 | 3 | kept | `제품명 "Roster", 가격, 문구는 모두 임시로 넣은 것입니다.` |
| c8625ea1 | 1 | kept | `#[cfg(test)]` |
| c8625ea1 | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| c8625ea1 | 3 | n/a | - |
| d9fd9748 | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| d9fd9748 | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| d9fd9748 | 3 | broken | `Ok(Err(e)) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),` |
| da929de3 | 1 | broken | `**바뀐 점**` |
| da929de3 | 2 | kept | `<Text style={heroKickerStyle}>Your account is ready</Text>` |
| da929de3 | 3 | kept | `Sign in to your dashboard` |
| f574fe7c | 1 | kept | `if self.history.len() == HISTORY_LEN {` |
| f574fe7c | 2 | n/a | - |
| f574fe7c | 3 | n/a | - |
| f85f9ab7 | 1 | n/a | `async fn joiner_gets_last_50_lines() {` |
| f85f9ab7 | 2 | n/a | - |
| f85f9ab7 | 3 | broken | `tokio::time::sleep(Duration::from_millis(100)).await;` |
