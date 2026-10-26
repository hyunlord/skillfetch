//! Stage 11 hidden check test (copied into a temp copy's tests/ by check.py).
use std::collections::{BTreeMap, HashSet};
use std::io::Cursor;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use image::{ImageFormat, RgbImage};
use tower::ServiceExt;

const BURST: usize = 48;

fn png(w: u32, h: u32) -> Vec<u8> {
    let img = RgbImage::from_fn(w, h, |x, y| image::Rgb([(x * 7 % 256) as u8, (y * 3 % 256) as u8, ((x + y) % 256) as u8]));
    let mut buf = Vec::new();
    img.write_to(&mut Cursor::new(&mut buf), ImageFormat::Png).unwrap();
    buf
}

#[test]
fn s11_probe() {
    let started = Arc::new(Mutex::new(Vec::new()));
    let s2 = started.clone();
    let rt = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .enable_all()
        .on_thread_start(move || s2.lock().unwrap().push(std::thread::current().id()))
        .build()
        .unwrap();
    // Worker threads: those started before any blocking task, plus every thread a plain async task runs on.
    let t0 = Instant::now();
    while started.lock().unwrap().len() < 2 && t0.elapsed() < Duration::from_secs(3) {
        std::thread::sleep(Duration::from_millis(2));
    }
    let mut workers: HashSet<_> = started.lock().unwrap().iter().cloned().collect();
    let seen = rt.block_on(async {
        let mut hs = Vec::new();
        for _ in 0..64 {
            hs.push(tokio::spawn(async {
                tokio::task::yield_now().await;
                std::thread::current().id()
            }));
        }
        let mut ids = Vec::new();
        for h in hs {
            ids.push(h.await.unwrap());
        }
        ids
    });
    workers.extend(seen);
    let n_workers = workers.len();
    image::__s11_probe::set_workers(workers);

    let img = png(1600, 1200);
    let app = cms_api::app(cms_api::AppState::new(cms_api::Config::default()));
    let out = rt.block_on(async move {
        // single request first: output dimensions
        let res = app.clone().oneshot(Request::post("/api/media/resize?w=400&h=400").body(Body::from(img.clone())).unwrap()).await.unwrap();
        let single_status = res.status().as_u16();
        let b = res.into_body().collect().await.unwrap().to_bytes();
        let single_dims = image::__s11_probe::quiet(|| image::load_from_memory(&b)).ok().map(|i| (i.width(), i.height()));

        image::__s11_probe::configure(300, BURST);
        let done = Arc::new(std::sync::atomic::AtomicBool::new(false));
        // latency sampler: other endpoints + timer lateness while the burst runs
        let (app2, done2) = (app.clone(), done.clone());
        let sampler = tokio::spawn(async move {
            let (mut lat_max, mut late_max, mut n, mut bad) = (0u128, 0u128, 0usize, 0usize);
            while !done2.load(std::sync::atomic::Ordering::SeqCst) {
                let t = Instant::now();
                tokio::time::sleep(Duration::from_millis(25)).await;
                late_max = late_max.max(t.elapsed().as_millis().saturating_sub(25));
                for path in ["/healthz", "/api/articles"] {
                    let t = Instant::now();
                    let r = app2.clone().oneshot(Request::get(path).body(Body::empty()).unwrap()).await.unwrap();
                    let _ = r.status().is_success() || { bad += 1; true };
                    lat_max = lat_max.max(t.elapsed().as_millis());
                    n += 1;
                }
            }
            (lat_max, late_max, n, bad)
        });
        tokio::time::sleep(Duration::from_millis(60)).await;
        let t = Instant::now();
        let mut hs = Vec::new();
        for _ in 0..BURST {
            let (a, body) = (app.clone(), img.clone());
            hs.push(tokio::spawn(async move {
                let r = a.oneshot(Request::post("/api/media/resize?w=400&h=400").body(Body::from(body)).unwrap()).await.unwrap();
                let st = r.status().as_u16();
                let b = r.into_body().collect().await.unwrap().to_bytes();
                let ok_dims = st != 200
                    || image::__s11_probe::quiet(|| image::load_from_memory(&b)).map(|i| i.width() <= 400 && i.height() <= 400).unwrap_or(false);
                (st, ok_dims)
            }));
        }
        let mut statuses = BTreeMap::new();
        let mut dims_ok = true;
        for h in hs {
            let (st, ok) = h.await.unwrap();
            *statuses.entry(st).or_insert(0usize) += 1;
            dims_ok &= ok;
        }
        let burst_ms = t.elapsed().as_millis();
        done.store(true, std::sync::atomic::Ordering::SeqCst);
        let (lat_max, late_max, n, bad) = sampler.await.unwrap();
        (single_status, single_dims, statuses, dims_ok, burst_ms, lat_max, late_max, n, bad)
    });
    let (calls, on_worker, max_conc) = image::__s11_probe::stats();
    let (single_status, single_dims, statuses, dims_ok, burst_ms, lat_max, late_max, n, bad) = out;
    println!(
        "S11_PROBE_RESULT {}",
        serde_json::json!({
            "workers": n_workers, "calls": calls, "on_worker": on_worker, "max_concurrency": max_conc,
            "single_status": single_status, "single_dims": single_dims, "statuses": statuses, "dims_ok": dims_ok,
            "burst_ms": burst_ms, "other_latency_max_ms": lat_max, "timer_lateness_max_ms": late_max,
            "other_requests": n, "other_failed": bad
        })
    );
}
