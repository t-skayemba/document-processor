"""
Deterministic checks on extracted invoice data.

The language model is good at reading a document but unreliable at arithmetic,
so it is asked to copy figures exactly as printed. These checks then compare
those figures in plain code and add a Flag for every inconsistency, so a bad
total or a missing tax number is caught every time rather than sometimes.

Entry points:
    validate_invoice(inv, document_text="") -> list[Flag]
    drop_contradicted_flags(flags, inv)     -> list[Flag]  (removes model flags the figures disprove)
    merge_flags(existing, new)              -> list[Flag]  (dedupes, sorts by severity)
"""
import logging
import re
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Tuple

from models.schemas import Flag, FlagSeverity, InvoiceData

# Allowed rounding difference between figures, in dollars.
TOLERANCE = 0.02

# Combined sales-tax rates seen on Canadian invoices:
# GST 5%, HST 13% (ON), HST 15% (Atlantic), GST+PST in BC/MB (12%), SK (11%), QC (14.975%).
CANADIAN_TAX_RATES = (0.05, 0.11, 0.12, 0.13, 0.14975, 0.15)

_CANADIAN_TAX_WORDS = re.compile(r"\b(HST|GST|QST|PST)\b", re.IGNORECASE)

logger = logging.getLogger(__name__)

_ORDER = {
    FlagSeverity.CRITICAL: 0,
    FlagSeverity.HIGH: 1,
    FlagSeverity.MEDIUM: 2,
    FlagSeverity.LOW: 3,
}


# --- helpers ----------------------------------------------------------------

def _num(value) -> Optional[float]:
    """Best-effort conversion of '$1,234.50', 1234.5 or '1 234,50' style values."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^\d.,\-()]", "", text)
    negative = text.startswith("(") and text.endswith(")") or text.startswith("-")
    text = text.strip("()-")
    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        # "1,234" is thousands; "1234,50" is a decimal comma
        text = text.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", text) else text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def _date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _is_canadian(inv: InvoiceData, document_text: str) -> bool:
    return (
        (inv.currency or "").strip().upper() == "CAD"
        or bool(_CANADIAN_TAX_WORDS.search(document_text or ""))
        or bool(_CANADIAN_TAX_WORDS.search(inv.tax_registration_number or ""))
    )


def _flag(issue: str, severity: FlagSeverity, location: str, recommendation: str) -> Flag:
    return Flag(issue=issue, severity=severity, location=location, recommendation=recommendation)


# --- individual checks ------------------------------------------------------

def _check_line_items(inv: InvoiceData) -> Tuple[List[Flag], List[float]]:
    flags: List[Flag] = []
    totals: List[float] = []
    all_numeric = True

    for index, item in enumerate(inv.line_items or [], start=1):
        if not isinstance(item, dict):
            all_numeric = False
            continue
        qty = _num(item.get("quantity"))
        unit = _num(item.get("unit_price"))
        line_total = _num(item.get("total"))
        label = (item.get("description") or f"line {index}").strip()

        if line_total is None:
            all_numeric = False
            continue
        totals.append(line_total)

        if qty is not None and unit is not None:
            expected = round(qty * unit, 2)
            if abs(expected - line_total) > TOLERANCE:
                flags.append(_flag(
                    f"Line {index} ('{label}') does not multiply out: "
                    f"{qty:g} x {_money(unit)} = {_money(expected)}, but the line total is {_money(line_total)}.",
                    FlagSeverity.MEDIUM,
                    f"Line items - row {index}",
                    "Confirm the quantity, rate and amount with the vendor before paying.",
                ))

    return flags, (totals if all_numeric and totals else [])


def _check_totals(inv: InvoiceData, line_totals: List[float]) -> List[Flag]:
    flags: List[Flag] = []
    subtotal, tax, total = _num(inv.subtotal), _num(inv.tax_amount), _num(inv.total_amount)

    if subtotal is not None and line_totals:
        line_sum = round(sum(line_totals), 2)
        if abs(line_sum - subtotal) > TOLERANCE:
            flags.append(_flag(
                f"Line items add up to {_money(line_sum)}, but the subtotal is {_money(subtotal)} "
                f"(difference {_money(abs(line_sum - subtotal))}). A line, discount or amount may be missing or wrong.",
                FlagSeverity.HIGH,
                "Line items vs. subtotal",
                "Ask the vendor for a corrected invoice or a breakdown of the difference.",
            ))

    if subtotal is not None and tax is not None and total is not None:
        expected = round(subtotal + tax, 2)
        diff = round(total - expected, 2)
        if abs(diff) > TOLERANCE:
            # Large gaps are critical; small ones may be rounding or a missing fee line.
            severity = FlagSeverity.CRITICAL if abs(diff) >= max(1.0, 0.01 * abs(total)) else FlagSeverity.HIGH
            direction = "higher" if diff > 0 else "lower"
            flags.append(_flag(
                f"The invoice total ({_money(total)}) does not match subtotal plus tax "
                f"({_money(subtotal)} + {_money(tax)} = {_money(expected)}). "
                f"The stated total is {_money(abs(diff))} {direction} than the figures support.",
                severity,
                "Totals block",
                "Do not pay until the vendor confirms the correct total and reissues the invoice.",
            ))

    return flags


def _check_tax_rate(inv: InvoiceData, document_text: str) -> List[Flag]:
    subtotal, tax = _num(inv.subtotal), _num(inv.tax_amount)
    if not subtotal or tax is None or subtotal <= 0 or tax <= 0:
        return []
    if not _is_canadian(inv, document_text):
        return []
    if any(abs(tax - round(subtotal * rate, 2)) <= max(TOLERANCE, 0.0005 * subtotal) for rate in CANADIAN_TAX_RATES):
        return []
    return [_flag(
        f"Tax of {_money(tax)} is {tax / subtotal:.2%} of the subtotal, which is not a standard Canadian sales-tax rate.",
        FlagSeverity.MEDIUM,
        "Tax line",
        "Confirm which tax applies (GST, HST, PST) and that the vendor calculated it correctly.",
    )]


def _check_registration(inv: InvoiceData, document_text: str) -> List[Flag]:
    tax = _num(inv.tax_amount)
    if not tax or tax <= 0 or (inv.tax_registration_number or "").strip():
        return []
    if not _is_canadian(inv, document_text):
        return []
    return [_flag(
        "The invoice charges sales tax but shows no GST/HST registration number.",
        FlagSeverity.MEDIUM,
        "Invoice header",
        "Request the vendor's GST/HST registration number; it is needed to claim input tax credits.",
    )]


def _check_dates(inv: InvoiceData) -> List[Flag]:
    flags: List[Flag] = []
    issued, due = _date(inv.issue_date), _date(inv.due_date)
    if not issued or not due:
        return flags

    if due < issued:
        flags.append(_flag(
            f"The due date ({due:%B %d, %Y}) is before the invoice date ({issued:%B %d, %Y}).",
            FlagSeverity.CRITICAL,
            "Invoice header - due date and invoice date",
            "Ask the vendor to correct the due date and reissue the invoice.",
        ))

    match = re.search(r"\bnet\s*(\d{1,3})\b", inv.payment_terms or "", re.IGNORECASE)
    if match:
        days = int(match.group(1))
        expected = issued + timedelta(days=days)
        if abs((due - expected).days) > 3:
            flags.append(_flag(
                f"Payment terms say Net {days}, which puts the due date around {expected:%B %d, %Y}, "
                f"but the invoice states {due:%B %d, %Y}.",
                FlagSeverity.HIGH,
                "Payment terms vs. due date",
                "Reconcile the due date with the stated terms.",
            ))

    return flags


# --- public API -------------------------------------------------------------

def validate_invoice(inv: Optional[InvoiceData], document_text: str = "") -> List[Flag]:
    """Run every deterministic check and return the flags it raises."""
    if inv is None:
        return []
    item_flags, line_totals = _check_line_items(inv)
    return (
        item_flags
        + _check_totals(inv, line_totals)
        + _check_tax_rate(inv, document_text)
        + _check_registration(inv, document_text)
        + _check_dates(inv)
    )


# A new flag is skipped when the model already raised the same issue.
# Each rule is a pair of regexes; a flag matches the rule when its text matches both.
_DUPLICATE_RULES = (
    (r"\btotal\b", r"match|add up|discrepan|incorrect|calculat|\bsum\b|does not|doesn't"),
    (r"subtotal", r"line item|add up|\bsum\b|discrepan"),
    (r"registration", r"gst|hst|tax"),
    (r"due date", r"before|earlier|preced|predate"),
    (r"due date", r"\bnet\b|payment terms|terms"),
    (r"\btax\b", r"rate|percent|%"),
)


def _matches(text: str, rule: Tuple[str, str]) -> bool:
    return all(re.search(pattern, text, re.IGNORECASE) for pattern in rule)


def _model_flag_text(flag: Flag) -> str:
    """Title plus location: model flags often put the useful words (e.g. 'TOTAL DUE line') in the location."""
    return f"{flag.issue} {flag.location or ''}"


def _matching_indexes(new: Flag, model_flags: List[Flag]) -> List[int]:
    """Positions of model flags that describe the same issue as `new`."""
    found = set()
    for rule in _DUPLICATE_RULES:
        if _matches(new.issue, rule):
            found.update(i for i, old in enumerate(model_flags) if _matches(_model_flag_text(old), rule))
    return sorted(found)


def merge_flags(existing: List[Flag], new: List[Flag]) -> List[Flag]:
    """
    Combine the model's flags with the deterministic ones, most severe first.

    When both describe the same issue, our computed flag replaces the model's (its wording is
    exact, and the model's title is sometimes misleading) and takes the higher of the two
    severities, so the model can never understate a verified problem. A model flag is only
    consumed once; two different checks never swallow each other.
    """
    model_flags = list(existing)
    merged = list(existing)
    removed: set = set()
    claimed: set = set()

    for flag in new:
        matches = _matching_indexes(flag, model_flags)
        free = [i for i in matches if i not in claimed]
        if not matches or not free:
            merged.append(flag)
            continue
        best = min([flag.severity] + [model_flags[i].severity for i in free], key=lambda sev: _ORDER[sev])
        merged[free[0]] = flag if best == flag.severity else flag.model_copy(update={"severity": best})
        removed.update(free[1:])
        claimed.update(free)

    return sorted((f for i, f in enumerate(merged) if i not in removed), key=lambda f: _ORDER[f.severity])


# --- removing model flags the figures disprove --------------------------------

_MISMATCH_WORDS = (
    r"not match|doesn't match|mismatch|discrepan|incorrect|does not add up|doesn't add up|overcharge|error"
)


def drop_contradicted_flags(flags: List[Flag], inv: Optional[InvoiceData]) -> List[Flag]:
    """
    The model sometimes raises a math flag whose own explanation says the numbers are fine.
    When the arithmetic has been verified in code, drop model flags that claim otherwise.
    Only math claims are touched; every other flag passes through unchanged.
    """
    if inv is None:
        return list(flags)

    subtotal, tax, total = _num(inv.subtotal), _num(inv.tax_amount), _num(inv.total_amount)
    _, line_totals = _check_line_items(inv)

    lines_ok = (
        subtotal is not None and bool(line_totals)
        and abs(round(sum(line_totals), 2) - subtotal) <= TOLERANCE
    )
    totals_ok = (
        subtotal is not None and tax is not None and total is not None
        and abs(round(subtotal + tax, 2) - total) <= TOLERANCE
    )

    kept: List[Flag] = []
    for flag in flags:
        claims_mismatch = re.search(_MISMATCH_WORDS, flag.issue, re.IGNORECASE)
        about_lines = re.search(r"\bsubtotal\b", flag.issue, re.IGNORECASE) and re.search(
            r"line item|sum of", flag.issue, re.IGNORECASE
        )
        about_total = re.search(r"\btotal\b", flag.issue, re.IGNORECASE) and not re.search(
            r"line item|sum of", flag.issue, re.IGNORECASE
        )
        if claims_mismatch and ((lines_ok and about_lines) or (totals_ok and about_total)):
            logger.info(f"Dropped model flag contradicted by verified figures: {flag.issue}")
            continue
        kept.append(flag)
    return kept
