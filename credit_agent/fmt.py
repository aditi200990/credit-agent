"""Formatting helpers."""


def inr(amount: float) -> str:
    """Format an amount in the Indian numbering system, e.g. 1200000 -> '₹12,00,000'."""
    n = int(round(amount))
    sign, s = ("-" if n < 0 else ""), str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"
