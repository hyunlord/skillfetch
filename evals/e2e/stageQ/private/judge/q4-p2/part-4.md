| code | rule | verdict | quote |
|---|---|---|---|
| 003a8eb0 | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 003a8eb0 | 2 | n/a | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 003a8eb0 | 3 | kept | `pub struct Rooms(pub Arc<Mutex<HashMap<String, Room>>>);` |
| 13a27e56 | 1 | kept | `with self.assertRaises(SystemExit):` |
| 13a27e56 | 2 | n/a | `from inventory.cli import load_items` |
| 13a27e56 | 3 | kept | `def test_empty_inventory_writes_header_only(self):` |
| 14dfe3e5 | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 14dfe3e5 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| 14dfe3e5 | 3 | broken | `return HTTPException(status.HTTP_404_NOT_FOUND, f"Bookmark {bookmark_id} not found")` |
| 1a495b18 | 1 | kept | `@app.get("/bookmarks/{bookmark_id}", response_model=Bookmark, responses=NOT_FOUND)` |
| 1a495b18 | 2 | kept | `raise DuplicateURLError(url) from exc` |
| 1a495b18 | 3 | kept | `f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 1f8fd94a | 1 | kept | `let result = tokio::task::spawn_blocking(move || {` |
| 1f8fd94a | 2 | kept | `pub resize_permits: Arc<Semaphore>,` |
| 1f8fd94a | 3 | broken | `.expect("resize semaphore closed");` |
| 373ee4bc | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| 373ee4bc | 2 | kept | `<Section style={heroStyle}>` |
| 373ee4bc | 3 | n/a | - |
| 38f9f8f0 | 1 | broken | `It loads its fonts (Schibsted Grotesk and IBM Plex Mono) through` |
| 38f9f8f0 | 2 | kept | `Keep one list of who&rsquo;s on your team.` |
| 38f9f8f0 | 3 | kept | `Try the demo directory` |
| 5fa3c7de | 1 | broken | `**Design:** cool white background, navy text, badge blue and lanyard yellow, with Bricolage Grotesque for headings and Public Sans for body text` |
| 5fa3c7de | 2 | kept | `One list of who&apos;s on your team. One URL to fetch it.` |
| 5fa3c7de | 3 | kept | `cta: "Start a 14-day Team trial",` |
| 71221d8d | 1 | n/a | - |
| 71221d8d | 2 | n/a | - |
| 71221d8d | 3 | kept | `# Same order_id with different contents: no way to tell which copy is right.` |
| 7362d133 | 1 | n/a | `{feature.icon}` |
| 7362d133 | 2 | n/a | `const LandingPage = () => (` |
| 7362d133 | 3 | n/a | `import Head from "next/head";` |
| 761dd27f | 1 | kept | `let result = tokio::task::spawn_blocking(move || {` |
| 761dd27f | 2 | n/a | `let Ok(permit) = state.resize_permits.clone().acquire_owned().await else {` |
| 761dd27f | 3 | kept | `resize_permits: Arc::new(Semaphore::new(config.max_concurrent_resizes.max(1))),` |
| 7a18e7c1 | 1 | broken | `I made up the product name "Roster", the copy and the prices` |
| 7a18e7c1 | 2 | kept | `<span className="accent">typed and lightning fast.</span>` |
| 7a18e7c1 | 3 | kept | `cta: "Start 14-day trial",` |
| 8628fe0e | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 8628fe0e | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| 8628fe0e | 3 | broken | `content={"detail": "A bookmark with this url already exists"},` |
| 88f94cd4 | 1 | kept | `let n = number.take().ok_or(ParseDurationError::MissingNumber)?;` |
| 88f94cd4 | 2 | kept | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 88f94cd4 | 3 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 9e82caea | 1 | kept | `Try the demo directory` |
| 9e82caea | 2 | broken | `**Hero:** headline "Keep one list of who's on your team."` |
| 9e82caea | 3 | kept | `**The prices ($0 / $24 / $79) and plan contents are made up.** Replace them before publishing.` |
| c7f0fc8a | 1 | kept | `<label htmlFor="waitlist-email" className={styles.formLabel}>` |
| c7f0fc8a | 2 | kept | `aria-describedby={error ? "waitlist-error" : undefined}` |
| c7f0fc8a | 3 | kept | `onClick={() => setSelectedId(user.id)}` |
