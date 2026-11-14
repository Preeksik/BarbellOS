"""Walidacja kodów EAN-8 / EAN-13 / UPC-A (cyfra kontrolna GS1)."""


def is_valid_ean(code: str) -> bool:
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    body, check = digits[:-1], digits[-1]
    # Wagi 3,1,3,1... licząc od prawej strony części bez cyfry kontrolnej.
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check
