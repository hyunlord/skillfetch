| code | rule | verdict | quote |
|---|---|---|---|
| 32c6dad9 | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 32c6dad9 | 2 | kept | `except sqlite3.IntegrityError as exc:` |
| 32c6dad9 | 3 | kept | `f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 3362d53e | 1 | kept | `@app.get("/bookmarks/{bookmark_id}", response_model=Bookmark, responses=NOT_FOUND)` |
| 3362d53e | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 3362d53e | 3 | broken | `return HTTPException(status.HTTP_409_CONFLICT, f"Bookmark with url {url!r} already exists")` |
| 3397d7f4 | 1 | n/a | `def test_missing_arguments(self):` |
| 3397d7f4 | 2 | n/a | `-` |
| 3397d7f4 | 3 | kept | `def test_writes_header_and_rows(self):` |
| 5574a544 | 1 | kept | `.ok_or(ParseDurationError::Overflow)?,` |
| 5574a544 | 2 | n/a | `-` |
| 5574a544 | 3 | kept | `Self::Overflow => f.write_str("duration too large"),` |
| 81537295 | 1 | kept | `#[cfg(test)]` |
| 81537295 | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 81537295 | 3 | kept | `tokio::task::yield_now().await;` |
| a221499c | 1 | kept | `resize_to_fit(&body, p.w, p.h)` |
| a221499c | 2 | kept | `pub resize_slots: Arc<Semaphore>,` |
| a221499c | 3 | broken | `.expect("resize semaphore is never closed");` |
| a5319dcd | 1 | n/a | `-` |
| a5319dcd | 2 | n/a | `-` |
| a5319dcd | 3 | kept | `pub resize_slots: Arc<Semaphore>,` |
| c19f2fad | 1 | kept | `#[cfg(test)]` |
| c19f2fad | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| c19f2fad | 3 | n/a | `-` |
| c859718c | 1 | kept | `<LinkButton href={link}>Sign in to your dashboard</LinkButton>` |
| c859718c | 2 | kept | `backgroundColor: "#e6f4f2",` |
| c859718c | 3 | n/a | `-` |
| c8990f67 | 1 | kept | `if tx.send(line.clone()).is_err() {` |
| c8990f67 | 2 | n/a | `-` |
| c8990f67 | 3 | n/a | `-` |
| cbe77524 | 1 | broken | `**바뀐 디자인**` |
| cbe77524 | 2 | broken | `<Text style={heroEyebrowStyle}>Account created</Text>` |
| cbe77524 | 3 | kept | `Go to Dashboard` |
| dae4ef85 | 1 | broken | `fontFamily: 'Consolas, Menlo, "Courier New", monospace',` |
| dae4ef85 | 2 | broken | `backgroundColor: "#e6f4f2",` |
| dae4ef85 | 3 | kept | `backgroundColor: "#00796b",` |
| de82d844 | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| de82d844 | 2 | kept | `- 외부 이미지, SVG, flex/grid, 미디어쿼리는 쓰지 않았어요.` |
| de82d844 | 3 | n/a | `-` |
| df9c0523 | 1 | kept | `#[cfg(test)]` |
| df9c0523 | 2 | n/a | `-` |
| df9c0523 | 3 | kept | `tokio::time::timeout(Duration::from_secs(2), lines.next_line()).await.unwrap().unwrap().unwrap()` |
| e11bee3e | 1 | n/a | `-` |
| e11bee3e | 2 | n/a | `export const getStaticProps: GetStaticProps<Props> = async () => ({` |
| e11bee3e | 3 | n/a | `-` |
| e4df205c | 1 | kept | `@router.get("", response_model=BookmarkListResponse)` |
| e4df205c | 2 | kept | `bookmark = BookmarkService(db).create(payload)` |
| e4df205c | 3 | kept | `"ORDER BY id DESC LIMIT ? OFFSET ?",` |
| e689bbb0 | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| e689bbb0 | 2 | kept | `except sqlite3.IntegrityError as exc:` |
| e689bbb0 | 3 | kept | `" ORDER BY b.id DESC LIMIT ? OFFSET ?",` |
| e82fb263 | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| e82fb263 | 2 | kept | `except repository.DuplicateURLError:` |
| e82fb263 | 3 | kept | `f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",` |
| e9f8a5ae | 1 | n/a | `-` |
| e9f8a5ae | 2 | n/a | `-` |
| e9f8a5ae | 3 | kept | `pub resize_permits: Arc<Semaphore>,` |
| fd4cb897 | 1 | kept | `@router.get("", response_model=BookmarkList)` |
| fd4cb897 | 2 | kept | `bookmark = service.create(payload)` |
| fd4cb897 | 3 | kept | `"ORDER BY id DESC LIMIT ? OFFSET ?",` |
