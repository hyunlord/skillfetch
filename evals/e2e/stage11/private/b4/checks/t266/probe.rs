//! Stage 11 check instrumentation, compiled into a patched copy of the `image` crate used only by the check's temp
//! copy of the worktree (never in the session's tree). `enter()` is called at the top of `decoder_to_image`, where every
//! public decode entry point of image 0.25 converges.
use std::cell::Cell;
use std::collections::HashSet;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Mutex;
use std::thread::{self, ThreadId};
use std::time::{Duration, Instant};

static WORKERS: Mutex<Option<HashSet<ThreadId>>> = Mutex::new(None);
static ON_WORKER: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static CUR: AtomicUsize = AtomicUsize::new(0);
static MAX: AtomicUsize = AtomicUsize::new(0);
static HOLD_MS: AtomicU64 = AtomicU64::new(0);
static TARGET: AtomicUsize = AtomicUsize::new(usize::MAX);

thread_local! {
    static QUIET: Cell<bool> = const { Cell::new(false) };
}

/// Runs `f` with the probe off on this thread (the check's own decodes of the responses).
pub fn quiet<R>(f: impl FnOnce() -> R) -> R {
    QUIET.with(|q| q.set(true));
    let r = f();
    QUIET.with(|q| q.set(false));
    r
}

pub fn set_workers(ids: HashSet<ThreadId>) {
    *WORKERS.lock().unwrap() = Some(ids);
}

pub fn configure(hold_ms: u64, target: usize) {
    HOLD_MS.store(hold_ms, Ordering::SeqCst);
    TARGET.store(target, Ordering::SeqCst);
}

/// (calls, calls on an async worker thread, max concurrent calls)
pub fn stats() -> (usize, usize, usize) {
    (CALLS.load(Ordering::SeqCst), ON_WORKER.load(Ordering::SeqCst), MAX.load(Ordering::SeqCst))
}

pub struct Guard(bool);

impl Drop for Guard {
    fn drop(&mut self) {
        if self.0 {
            CUR.fetch_sub(1, Ordering::SeqCst);
        }
    }
}

pub fn enter() -> Guard {
    if QUIET.with(|q| q.get()) {
        return Guard(false);
    }
    if WORKERS.lock().unwrap().as_ref().is_some_and(|w| w.contains(&thread::current().id())) {
        ON_WORKER.fetch_add(1, Ordering::SeqCst);
    }
    CALLS.fetch_add(1, Ordering::SeqCst);
    let c = CUR.fetch_add(1, Ordering::SeqCst) + 1;
    MAX.fetch_max(c, Ordering::SeqCst);
    // Hold the call until `target` calls are in flight (or hold_ms passes), so an unbounded burst shows its full width.
    let t0 = Instant::now();
    let hold = Duration::from_millis(HOLD_MS.load(Ordering::SeqCst));
    while t0.elapsed() < hold && CUR.load(Ordering::SeqCst) < TARGET.load(Ordering::SeqCst) {
        thread::sleep(Duration::from_millis(5));
    }
    Guard(true)
}
