| code | rule | verdict | quote |
|---|---|---|---|
| 0643922a | 1 | kept | `@app.get("/bookmarks", response_model=BookmarkList)` |
| 0643922a | 2 | kept | `raise DuplicateURLError(url) from exc` |
| 0643922a | 3 | kept | `f"SELECT * FROM bookmarks {where} ORDER BY id DESC LIMIT ? OFFSET ?",` |
| 2b7002da | 1 | broken | `Get started free` |
| 2b7002da | 2 | broken | `Your team directory,` |
| 2b7002da | 3 | kept | `I made up the product name "Roster", the copy and the prices` |
| 31b74e10 | 1 | broken | `font-family:-apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif` |
| 31b74e10 | 2 | broken | `backgroundColor: "#00796b",` |
| 31b74e10 | 3 | kept | `backgroundColor: "#00796b",` |
| 36c8338b | 1 | n/a | `pub fn parse_duration(s: &str) -> Result<Duration, ParseDurationError> {` |
| 36c8338b | 2 | kept | `.ok_or(ParseDurationError::Overflow)?;` |
| 36c8338b | 3 | kept | `impl Error for ParseDurationError {}` |
| 3866fe11 | 1 | kept | `Try the demo roster` |
| 3866fe11 | 2 | broken | `One list of who&apos;s on your team. One URL to fetch it.` |
| 3866fe11 | 3 | kept | `Pricing and plan details are placeholders I made up.` |
| 389a2dfa | 1 | n/a | - |
| 389a2dfa | 2 | n/a | `export const getStaticProps: GetStaticProps<Props> = async () => ({` |
| 389a2dfa | 3 | n/a | `const WaitlistForm = () => {` |
| 3e7f2575 | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| 3e7f2575 | 2 | kept | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| 3e7f2575 | 3 | kept | `mutex를 잡은 상태에서 이루어집니다. 그래서 history를 보내는 도중에 다른 메시지가 끼어들 수 없고` |
| 449dc41c | 1 | n/a | - |
| 449dc41c | 2 | n/a | - |
| 449dc41c | 3 | kept | `Dates after today are treated as data-entry errors -> null.` |
| 44d873f6 | 1 | n/a | `def test_missing_arguments(self):` |
| 44d873f6 | 2 | n/a | `from tools.export_csv import COLUMNS, main` |
| 44d873f6 | 3 | kept | `def test_writes_header_and_rows(self):` |
| 5e2fef6f | 1 | broken | `fontFamily: 'Consolas, Menlo, "Courier New", monospace',` |
| 5e2fef6f | 2 | broken | `backgroundColor: "#e6f4f2",` |
| 5e2fef6f | 3 | kept | `backgroundColor: "#00796b",` |
| 5fe770da | 1 | kept | `<Button href={link} style={buttonStyle}>` |
| 5fe770da | 2 | kept | `레이아웃은 표 기반이고, flex, grid, 웹폰트, 외부 이미지는 쓰지 않았습니다.` |
| 5fe770da | 3 | n/a | `신규 가입 환영 이메일을 다시 디자인했습니다.` |
| a099ff43 | 1 | broken | `**디자인:** "출석부"를 콘셉트로, 연한 세이지색 종이 배경, 남색 잉크, 볼펜 파랑, 형광펜 노랑을 썼습니다.` |
| a099ff43 | 2 | kept | `Everyone on your team, in one list your code can read.` |
| a099ff43 | 3 | kept | `setError("Enter an email address like name@company.com.");` |
| a99d0a1e | 1 | broken | `**섹션별 구성**` |
| a99d0a1e | 2 | kept | `Everyone on your team, one link away.` |
| a99d0a1e | 3 | kept | `setError("That email is missing something. Use the format name@company.com.");` |
| b1d9a52d | 1 | broken | `**바뀐 디자인**` |
| b1d9a52d | 2 | broken | `<Text style={heroEyebrowStyle}>Account created</Text>` |
| b1d9a52d | 3 | kept | `Go to Dashboard` |
| c81b7107 | 1 | broken | `**What I assumed about the product**` |
| c81b7107 | 2 | kept | `Keep one list of who&rsquo;s on your team.` |
| c81b7107 | 3 | kept | `Try the demo directory` |
| c83a0424 | 1 | kept | `tokio::time::timeout(Duration::from_secs(2), lines.next_line()).await.unwrap().unwrap().unwrap()` |
| c83a0424 | 2 | kept | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| c83a0424 | 3 | kept | `pub struct Rooms(pub Arc<Mutex<HashMap<String, Room>>>);` |
| e01105d8 | 1 | kept | `#[cfg(test)]` |
| e01105d8 | 2 | kept | `assert_eq!(parse_duration(""), Err(ParseDurationError::Empty));` |
| e01105d8 | 3 | n/a | - |
| f189a148 | 1 | broken | `Get started free` |
| f189a148 | 2 | broken | `The simplest way to <span className={styles.accent}>manage your users</span>` |
| f189a148 | 3 | kept | `제품명 "Roster", 가격, 문구는 모두 임시로 넣은 것입니다.` |
| f7936cf4 | 1 | kept | `@app.get("/bookmarks/{bookmark_id}", response_model=Bookmark)` |
| f7936cf4 | 2 | kept | `response.headers["Location"] = f"/bookmarks/{bookmark['id']}"` |
| f7936cf4 | 3 | broken | `content={"detail": "A bookmark with this url already exists"},` |
| fd898910 | 1 | kept | `tokio::time::sleep(Duration::from_millis(100)).await;` |
| fd898910 | 2 | kept | `pub fn join(&mut self, id: u64, tx: UnboundedSender<String>) {` |
| fd898910 | 3 | kept | `이 처리는 서버가 방 전체 lock을 잡은 상태에서 일어납니다.` |
