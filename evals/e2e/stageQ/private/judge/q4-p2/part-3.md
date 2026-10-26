| code | rule | verdict | quote |
|---|---|---|---|
| 0cba8906 | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 0cba8906 | 2 | broken | `impl std::error::Error for ParseDurationError {}` |
| 0cba8906 | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 1b5aef00 | 1 | kept | `tokio::time::timeout(Duration::from_secs(2), lines.next_line()).await.unwrap().unwrap().unwrap()` |
| 1b5aef00 | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 1b5aef00 | 3 | kept | `pub struct Rooms(pub Arc<Mutex<HashMap<String, Room>>>);` |
| 3599919c | 1 | broken | `Get started free` |
| 3599919c | 2 | broken | `- **CTA:** a gradient banner with a "Launch Roster" button, followed by a footer.` |
| 3599919c | 3 | broken | `features: ["SSO & audit logs", "Dedicated infrastructure", "99.9% SLA"],` |
| 3ce8757a | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 3ce8757a | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 3ce8757a | 3 | kept | `이 과정이 방 잠금(Mutex)을 쥔 채로 진행되므로, 지난 메시지가 다 들어간 다음에야 새 메시지가 도착합니다.` |
| 3e9416f1 | 1 | kept | `#[cfg(test)]` |
| 3e9416f1 | 2 | n/a | `pub fn broadcast(&mut self, from: u64, text: &str) {` |
| 3e9416f1 | 3 | broken | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 3f9a846f | 1 | broken | `**디자인:** "출석부"를 콘셉트로, 연한 세이지색 종이 배경, 남색 잉크, 볼펜 파랑, 형광펜 노랑을 썼습니다.` |
| 3f9a846f | 2 | kept | `Everyone on your team, in one list your code can read.` |
| 3f9a846f | 3 | kept | `setError("Enter an email address like name@company.com.");` |
| 4344dd30 | 1 | kept | `with self.assertRaises(SystemExit):` |
| 4344dd30 | 2 | n/a | `subprocess.run([sys.executable, str(SCRIPT), str(DEFAULT), str(self.out)], check=True)` |
| 4344dd30 | 3 | kept | `def test_writes_selected_columns(self):` |
| 4cf81cf8 | 1 | kept | `app.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])` |
| 4cf81cf8 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 4cf81cf8 | 3 | broken | `return HTTPException(status.HTTP_404_NOT_FOUND, f"Bookmark {bookmark_id} not found")` |
| 58b4eaf5 | 1 | broken | `font-family:-apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif` |
| 58b4eaf5 | 2 | broken | `backgroundColor: "#00796b",` |
| 58b4eaf5 | 3 | kept | `color: "#b2dfdb",` |
| 5ce1bb9f | 1 | kept | `#[cfg(test)]` |
| 5ce1bb9f | 2 | kept | `/// assert!(parse_duration("1x").is_err());` |
| 5ce1bb9f | 3 | n/a | - |
| 60c34c4a | 1 | n/a | - |
| 60c34c4a | 2 | n/a | - |
| 60c34c4a | 3 | kept | `# Same order_id with different contents: no way to tell which version is right, so reject all.` |
| 6c992816 | 1 | n/a | `def test_empty_inventory_writes_header_only(self):` |
| 6c992816 | 2 | n/a | - |
| 6c992816 | 3 | kept | `def test_quotes_names_containing_commas(self):` |
| 6cafb35c | 1 | kept | `app.include_router(bookmarks.router, prefix="/bookmarks", tags=["bookmarks"])` |
| 6cafb35c | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark.id}"` |
| 6cafb35c | 3 | broken | `return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})` |
| 8d6c06a2 | 1 | n/a | - |
| 8d6c06a2 | 2 | n/a | - |
| 8d6c06a2 | 3 | kept | `Dates after today are treated as data-entry errors -> null.` |
| ac0a9f29 | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| ac0a9f29 | 2 | broken | `impl Error for ParseDurationError {}` |
| ac0a9f29 | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| b395b62d | 1 | kept | `#[cfg(test)]` |
| b395b62d | 2 | kept | `let err = parse_duration("5d").unwrap_err();` |
| b395b62d | 3 | n/a | - |
| d1d0f560 | 1 | kept | `<label htmlFor="signup-email" className={styles.label}>` |
| d1d0f560 | 2 | kept | `role={error ? "alert" : "status"}` |
| d1d0f560 | 3 | kept | `type="button"` |
| e2657122 | 1 | broken | `**구성**` |
| e2657122 | 2 | broken | `<span className={styles.badge}>New · JSON API included</span>` |
| e2657122 | 3 | kept | `cta: "Start 14-day trial",` |
| ea0719c4 | 1 | kept | `cta: "Start a 14-day Team trial",` |
| ea0719c4 | 2 | broken | `One list of who&apos;s on your team. One URL to fetch it.` |
| ea0719c4 | 3 | kept | `- **Pricing and plan details are placeholders I made up.** Change them to your real terms before publishing. I didn't add any customer numbers or testimonials.` |
| ef9107b8 | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| ef9107b8 | 2 | kept | `<Section style={heroStyle}>` |
| ef9107b8 | 3 | n/a | - |
