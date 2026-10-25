// Hidden check for t016 (stage 10): history replay on join, last 50 messages per room, in order.
use std::time::Duration;

use chat_server::{room::Rooms, server};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader, Lines};
use tokio::net::tcp::{OwnedReadHalf, OwnedWriteHalf};
use tokio::net::{TcpListener, TcpStream};

async fn start() -> String {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap().to_string();
    tokio::spawn(server::run(listener, Rooms::default()));
    addr
}

async fn client(addr: &str, room: &str) -> (Lines<BufReader<OwnedReadHalf>>, OwnedWriteHalf) {
    let s = TcpStream::connect(addr).await.unwrap();
    let (r, mut w) = s.into_split();
    w.write_all(format!("JOIN {room}\n").as_bytes()).await.unwrap();
    (BufReader::new(r).lines(), w)
}

async fn next(lines: &mut Lines<BufReader<OwnedReadHalf>>, ms: u64) -> Option<String> {
    match tokio::time::timeout(Duration::from_millis(ms), lines.next_line()).await {
        Ok(Ok(Some(l))) => Some(l),
        _ => None,
    }
}

/// `sender` posts `n` lines `<tag>-<i>`; `witness` (already in the room) reads them all so we know they were broadcast.
async fn post(sender: &mut OwnedWriteHalf, witness: &mut Lines<BufReader<OwnedReadHalf>>, tag: &str, n: usize) {
    for i in 0..n {
        sender.write_all(format!("{tag}-{i}\n").as_bytes()).await.unwrap();
    }
    for i in 0..n {
        let l = next(witness, 2000).await.unwrap_or_else(|| panic!("witness missed {tag}-{i}"));
        assert!(l.ends_with(&format!("{tag}-{i}")), "witness got {l}");
    }
}

async fn drain(lines: &mut Lines<BufReader<OwnedReadHalf>>) -> Vec<String> {
    let mut got = Vec::new();
    while let Some(l) = next(lines, 500).await {
        got.push(l);
    }
    got
}

#[tokio::test]
async fn joiner_gets_last_50_in_order() {
    let addr = start().await;
    let (_ar, mut aw) = client(&addr, "lobby").await;
    let (mut wr, _ww) = client(&addr, "lobby").await;
    tokio::time::sleep(Duration::from_millis(100)).await;
    post(&mut aw, &mut wr, "msg", 60).await;
    let (mut br, _bw) = client(&addr, "lobby").await;
    let got = drain(&mut br).await;
    assert_eq!(got.len(), 50, "replayed {} lines: {:?}", got.len(), got.iter().take(3).collect::<Vec<_>>());
    for (k, l) in got.iter().enumerate() {
        assert!(l.ends_with(&format!("msg-{}", 10 + k)), "line {k} was {l}");
    }
    aw.write_all(b"after\n").await.unwrap();
    let l = next(&mut br, 2000).await.expect("no live message after replay");
    assert!(l.ends_with("after"), "{l}");
}

#[tokio::test]
async fn short_history_is_replayed_whole() {
    let addr = start().await;
    let (_ar, mut aw) = client(&addr, "small").await;
    let (mut wr, _ww) = client(&addr, "small").await;
    tokio::time::sleep(Duration::from_millis(100)).await;
    post(&mut aw, &mut wr, "m", 3).await;
    let (mut br, _bw) = client(&addr, "small").await;
    let got = drain(&mut br).await;
    assert_eq!(got.len(), 3, "{got:?}");
    for (k, l) in got.iter().enumerate() {
        assert!(l.ends_with(&format!("m-{k}")), "{l}");
    }
}

#[tokio::test]
async fn history_is_per_room() {
    let addr = start().await;
    let (_ar, mut aw) = client(&addr, "x").await;
    let (mut wr, _ww) = client(&addr, "x").await;
    tokio::time::sleep(Duration::from_millis(100)).await;
    post(&mut aw, &mut wr, "only-x", 5).await;
    let (mut yr, _yw) = client(&addr, "y").await;
    assert!(drain(&mut yr).await.is_empty(), "room y replayed room x history");
}

#[tokio::test]
async fn empty_room_replays_nothing() {
    let addr = start().await;
    let (mut br, _bw) = client(&addr, "fresh").await;
    assert!(drain(&mut br).await.is_empty());
}
