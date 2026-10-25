// Hidden check for t263 (stage 10): parsing a 2,000-level snapshot allocates O(1)-ish, not once per field.
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};

use market_data::feed::l2::parse_order_book;

struct Counting;
static ALLOCS: AtomicUsize = AtomicUsize::new(0);
unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::SeqCst);
        System.alloc(l)
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        System.dealloc(p, l)
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::SeqCst);
        System.realloc(p, l, n)
    }
}
#[global_allocator]
static A: Counting = Counting;

#[test]
fn few_allocations_for_a_deep_book() {
    let bids: Vec<String> = (0..1000).map(|i| format!("{}.{:02}x{}", 1000 - i / 100, i % 100, i % 7 + 1)).collect();
    let asks: Vec<String> = (0..1000).map(|i| format!("{}.{:02}x{}", 1001 + i / 100, i % 100, i % 5 + 1)).collect();
    let line = format!("BTC-USD|B:{}|A:{}", bids.join(","), asks.join(","));
    let before = ALLOCS.load(Ordering::SeqCst);
    let book = parse_order_book(&line).unwrap();
    let used = ALLOCS.load(Ordering::SeqCst) - before;
    assert_eq!(book.bids.len() + book.asks.len(), 2000);
    assert!(used <= 40, "{used} allocations for 2,000 levels");
}
