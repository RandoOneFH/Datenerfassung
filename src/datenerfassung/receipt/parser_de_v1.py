from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class ParsedLine:
    name_raw: str
    quantity: float | None = None
    unit_price: float | None = None
    total: float | None = None


@dataclass(frozen=True, slots=True)
class ParsedReceipt:
    merchant_name_hint: str | None
    datetime_hint: datetime | None
    lines: list[ParsedLine]


_DATE = re.compile(r"\b(\d{2})[./-](\d{2})[./-](\d{4})\b")
_TIME = re.compile(r"\b(\d{2}):(\d{2})\b")
_PRICE = re.compile(r"(?P<price>\d+[\.,]\d{2})\s*$")


def parse_receipt_text(text: str, *, tz: str = "Europe/Berlin") -> ParsedReceipt:
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    dt_hint = _parse_datetime_hint(text, tz=tz)

    merchant_hint = None
    if lines:
        merchant_hint = lines[0][:80]

    parsed_lines: list[ParsedLine] = []
    for ln in lines:
        if _is_noise_line(ln):
            continue
        parsed_lines.append(_parse_line(ln))

    return ParsedReceipt(merchant_name_hint=merchant_hint, datetime_hint=dt_hint, lines=parsed_lines)


def _parse_datetime_hint(text: str, *, tz: str) -> datetime | None:
    date_match = _DATE.search(text)
    if not date_match:
        return None

    day, month, year = map(int, date_match.groups())
    time_match = _TIME.search(text)
    hour, minute = (0, 0)
    if time_match:
        hour, minute = map(int, time_match.groups())

    try:
        zone = ZoneInfo(tz)
    except Exception:
        zone = datetime.now().astimezone().tzinfo or timezone.utc
    return datetime(year, month, day, hour, minute, tzinfo=zone)


def _is_noise_line(line: str) -> bool:
    lower = line.casefold()
    return any(
        marker in lower
        for marker in [
            "summe",
            "gesamt",
            "total",
            "mwst",
            "ust",
            "steuern",
            "bar",
            "karte",
            "ec",
            "visa",
        ]
    )


def _parse_line(line: str) -> ParsedLine:
    m = _PRICE.search(line)
    if not m:
        return ParsedLine(name_raw=line)

    price = _parse_price(m.group("price"))
    name_part = line[: m.start("price")].strip()

    qty_m = re.search(r"\b(?P<qty>\d+(?:[\.,]\d+)?)\s*[x\*]\s*$", name_part)
    if qty_m:
        qty = _parse_number(qty_m.group("qty"))
        name_part = name_part[: qty_m.start()].strip()
        if qty and price is not None:
            unit_price = price
            total = round(qty * unit_price, 2)
            return ParsedLine(name_raw=name_part, quantity=qty, unit_price=unit_price, total=total)

    return ParsedLine(name_raw=name_part or line, quantity=1.0, unit_price=price, total=price)


def _parse_price(value: str) -> float | None:
    return _parse_number(value)


def _parse_number(value: str) -> float | None:
    value = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None
