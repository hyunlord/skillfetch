| code | rule | verdict | quote |
|---|---|---|---|
| 04e952b8 | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| 04e952b8 | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 04e952b8 | 3 | broken | `.expect("resize semaphore closed");` |
| 0df00679 | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| 0df00679 | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 0df00679 | 3 | broken | `.expect("resize semaphore closed");` |
| 1bcc14bb | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| 1bcc14bb | 2 | kept | `- 외부 이미지, SVG, flex/grid, 미디어쿼리는 쓰지 않았어요.` |
| 1bcc14bb | 3 | n/a | `-` |
| 35668013 | 1 | kept | `app.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])` |
| 35668013 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 35668013 | 3 | broken | `return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})` |
| 3e0ae670 | 1 | n/a | `-` |
| 3e0ae670 | 2 | n/a | `.acquire_owned()` |
| 3e0ae670 | 3 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 4ddbcfa9 | 1 | kept | `.ok_or(ParseDurationError::Overflow)?,` |
| 4ddbcfa9 | 2 | n/a | `-` |
| 4ddbcfa9 | 3 | kept | `Self::Overflow => f.write_str("duration too large"),` |
| 5a42cb15 | 1 | kept | `self.history.push_back(line);` |
| 5a42cb15 | 2 | n/a | `-` |
| 5a42cb15 | 3 | n/a | `-` |
| 5d1a32f6 | 1 | kept | `<label htmlFor="signup-email" className={styles.label}>` |
| 5d1a32f6 | 2 | kept | `role={error ? "alert" : "status"}` |
| 5d1a32f6 | 3 | kept | `onClick={() => setSelectedId(person.id)}` |
| 7d68851e | 1 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 7d68851e | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 7d68851e | 3 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 9c838f2b | 1 | kept | `<label htmlFor="waitlist-email" className={styles.formLabel}>` |
| 9c838f2b | 2 | kept | `<p id="waitlist-error" role="alert" className={styles.formError}>` |
| 9c838f2b | 3 | kept | `onClick={() => setSelectedId(user.id)}` |
| a665ca1a | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| a665ca1a | 2 | kept | `pub resize_slots: Arc<Semaphore>,` |
| a665ca1a | 3 | broken | `.expect("resize semaphore is never closed");` |
| b2e55fc4 | 1 | broken | `**What's on the page:**` |
| b2e55fc4 | 2 | broken | `<span className="accent">typed and lightning fast.</span>` |
| b2e55fc4 | 3 | kept | `cta: "Start 14-day trial",` |
| b3103546 | 1 | kept | `with self.assertRaises(SystemExit):` |
| b3103546 | 2 | n/a | `-` |
| b3103546 | 3 | kept | `def test_writes_selected_columns(self):` |
| b70e5eb7 | 1 | kept | `#[cfg(test)]` |
| b70e5eb7 | 2 | kept | `let err = parse_duration("5d").unwrap_err();` |
| b70e5eb7 | 3 | n/a | `-` |
| bd30bfff | 1 | n/a | `-` |
| bd30bfff | 2 | n/a | `-` |
| bd30bfff | 3 | n/a | `-` |
| c038fcee | 1 | kept | `"/bookmarks/{bookmark_id}",` |
| c038fcee | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| c038fcee | 3 | broken | `return HTTPException(status.HTTP_404_NOT_FOUND, f"Bookmark {bookmark_id} not found")` |
| cdcdbbf7 | 1 | n/a | `-` |
| cdcdbbf7 | 2 | n/a | `-` |
| cdcdbbf7 | 3 | kept | `# Same order_id with different contents: no way to tell which copy is right.` |
| d30305ca | 1 | kept | `#[cfg(test)]` |
| d30305ca | 2 | kept | `assert!(parse_duration("1h30").is_err());` |
| d30305ca | 3 | n/a | `-` |
| d39e0aea | 1 | broken | `cool white background, navy text, badge blue and lanyard yellow` |
| d39e0aea | 2 | kept | `One list of who&apos;s on your team. One URL to fetch it.` |
| d39e0aea | 3 | kept | `cta: "Start a 14-day Team trial",` |
| d5b8b19e | 1 | kept | `let result = tokio::task::spawn_blocking(move` |
| d5b8b19e | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| d5b8b19e | 3 | broken | `Ok(Err(e)) => (StatusCode::BAD_REQUEST, e.to_string()).into_response(),` |
