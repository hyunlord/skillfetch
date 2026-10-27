"""Pricing calculations."""


def calculate_total(
    unit_price: float, quantity: int, discount_pct: float = 0.0
) -> float:
    """Calculate order total with optional discount."""
    subtotal = unit_price * quantity
    discount = subtotal * (discount_pct / 100)
    return round(subtotal - discount, 2)


def apply_tax(amount: float, tax_rate: float = 0.1) -> float:
    """Apply tax rate to amount."""
    return round(amount * (1 + tax_rate), 2)
