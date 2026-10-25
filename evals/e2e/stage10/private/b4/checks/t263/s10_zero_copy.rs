// Hidden check for t263 (stage 10): parsed fields borrow from the input line (no copies), values unchanged.
use market_data::feed::l2::parse_order_book;

fn inside(input: &str, p: *const u8) -> bool {
    let start = input.as_ptr() as usize;
    let p = p as usize;
    p >= start && p < start + input.len()
}

#[test]
fn fields_point_into_the_input() {
    let input = String::from("BTC-USD|B:101.25x3.0,101.00x1.5,100.75x9|A:101.50x2.0,101.75x4.25");
    let book = parse_order_book(&input).unwrap();
    assert!(inside(&input, book.symbol.as_ptr()), "symbol is a copy");
    for l in book.bids.iter().chain(book.asks.iter()) {
        assert!(inside(&input, l.price.as_ptr()), "price {} is a copy", l.price);
        assert!(inside(&input, l.size.as_ptr()), "size {} is a copy", l.size);
    }
}

#[test]
fn values_are_unchanged() {
    let input = String::from("ETH-USD|B:3001.5x0.2,3001.25x7|A:3002x1.125");
    let book = parse_order_book(&input).unwrap();
    assert_eq!(book.symbol, "ETH-USD");
    let bids: Vec<(String, String)> = book.bids.iter().map(|l| (l.price.to_string(), l.size.to_string())).collect();
    let asks: Vec<(String, String)> = book.asks.iter().map(|l| (l.price.to_string(), l.size.to_string())).collect();
    assert_eq!(bids, vec![("3001.5".into(), "0.2".into()), ("3001.25".into(), "7".into())]);
    assert_eq!(asks, vec![("3002".into(), "1.125".into())]);
}
