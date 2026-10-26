| code | rule | verdict | quote |
|---|---|---|---|
| 0012f813 | 1 | n/a | - |
| 0012f813 | 2 | n/a | - |
| 0012f813 | 3 | kept | `# Same order_id with different contents: no way to tell which version is right, so reject all.` |
| 07371c5b | 1 | n/a | - |
| 07371c5b | 2 | n/a | - |
| 07371c5b | 3 | kept | `같은 주문번호인데 수량이나 상태가 다른 3건(6행)은 어느 쪽이 맞는지 알 수 없어서 모두 제외했습니다.` |
| 143a385a | 1 | kept | `#[cfg(test)]` |
| 143a385a | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 143a385a | 3 | kept | `tokio::time::timeout(Duration::from_secs(2), lines.next_line()).await.unwrap().unwrap().unwrap()` |
| 1608caf8 | 1 | broken | `**바뀐 점**` |
| 1608caf8 | 2 | kept | `<Text style={heroKickerStyle}>Your account is ready</Text>` |
| 1608caf8 | 3 | kept | `Sign in to your dashboard` |
| 1f5f0036 | 1 | n/a | - |
| 1f5f0036 | 2 | n/a | - |
| 1f5f0036 | 3 | kept | `def test_quotes_names_with_commas(self):` |
| 290fd731 | 1 | n/a | - |
| 290fd731 | 2 | n/a | - |
| 290fd731 | 3 | kept | `def test_quotes_names_containing_commas(self):` |
| 2dcbe8df | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 2dcbe8df | 2 | kept | `raise DuplicateURLError(url) from exc` |
| 2dcbe8df | 3 | kept | `f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 2f171330 | 1 | n/a | - |
| 2f171330 | 2 | n/a | - |
| 2f171330 | 3 | kept | `pub resize_slots: Arc<Semaphore>,` |
| 3bc0744b | 1 | broken | `**구성**` |
| 3bc0744b | 2 | broken | `<span className={styles.badge}>New · JSON API included</span>` |
| 3bc0744b | 3 | kept | `Get started free` |
| 5a90c18e | 1 | kept | `#[cfg(test)]` |
| 5a90c18e | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 5a90c18e | 3 | kept | `tokio::time::timeout(Duration::from_secs(2), async {` |
| 659fc1b7 | 1 | kept | `std::time::Duration::from_millis(200),` |
| 659fc1b7 | 2 | n/a | - |
| 659fc1b7 | 3 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 666348ce | 1 | kept | `app.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])` |
| 666348ce | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 666348ce | 3 | broken | `assert resp.json()["detail"] == "Bookmark 999 not found"` |
| 687a6238 | 1 | kept | `"/bookmarks",` |
| 687a6238 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 687a6238 | 3 | broken | `assert "already exists" in resp.json()["detail"]` |
| 7035a174 | 1 | kept | `#[cfg(test)]` |
| 7035a174 | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 7035a174 | 3 | broken | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 7fe854a0 | 1 | kept | `#[cfg(test)]` |
| 7fe854a0 | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| 7fe854a0 | 3 | n/a | - |
| 830a4bb9 | 1 | kept | `@router.get("", response_model=BookmarkList)` |
| 830a4bb9 | 2 | kept | `class BookmarkService:` |
| 830a4bb9 | 3 | kept | `"ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 97f09db4 | 1 | kept | `#[cfg(test)]` |
| 97f09db4 | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| 97f09db4 | 3 | n/a | - |
| b9e5a6e8 | 1 | n/a | - |
| b9e5a6e8 | 2 | n/a | - |
| b9e5a6e8 | 3 | n/a | - |
| d0338889 | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| d0338889 | 2 | kept | `raise DuplicateURLError(url) from exc` |
| d0338889 | 3 | kept | `limit: Annotated[int, Query(ge=1, le=100)] = 20,` |
| f45a9699 | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| f45a9699 | 2 | n/a | - |
| f45a9699 | 3 | n/a | `history: VecDeque<String>,` |
