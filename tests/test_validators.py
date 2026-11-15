from agent.validators import _num, drop_contradicted_flags, merge_flags, validate_invoice
from models.schemas import Flag, FlagSeverity, InvoiceData

LINES = [
    {"description": "Document scanning and indexing", "quantity": 40, "unit_price": 85.00, "total": 3400.00},
    {"description": "Records retrieval (courier)", "quantity": 6, "unit_price": 45.00, "total": 270.00},
    {"description": "Secure storage, Q4 2026", "quantity": 1, "unit_price": 620.00, "total": 620.00},
    {"description": "Rush handling surcharge", "quantity": 1, "unit_price": 150.00, "total": 150.00},
]


def make(**overrides) -> InvoiceData:
    data = dict(
        invoice_number="HDS-20931",
        vendor_name="Harborview Document Services Inc.",
        client_name="Maplewood Professional Services LLP",
        issue_date="2026-10-03",
        due_date="2026-11-02",
        subtotal=4440.00,
        tax_amount=577.20,
        total_amount=5017.20,
        currency="CAD",
        line_items=LINES,
        payment_terms="Net 30",
        tax_registration_number="812345678 RT0001",
    )
    data.update(overrides)
    return InvoiceData(**data)


def issues(flags):
    return [f.issue for f in flags]


def test_clean_invoice_raises_nothing():
    assert validate_invoice(make()) == []


def test_original_demo_sample_total_error_is_critical():
    # The $200 error that the model-only version missed: 4,440.00 + 577.20 = 5,017.20, not 5,217.20.
    flags = validate_invoice(make(total_amount=5217.20))
    total_flags = [f for f in flags if "does not match subtotal plus tax" in f.issue]
    assert len(total_flags) == 1
    assert total_flags[0].severity == FlagSeverity.CRITICAL
    assert "$200.00" in total_flags[0].issue


def test_original_demo_sample_all_planted_issues():
    flags = validate_invoice(
        make(total_amount=5217.20, due_date="2026-09-19", tax_registration_number=None)
    )
    text = " ".join(issues(flags))
    assert "does not match subtotal plus tax" in text
    assert "before the invoice date" in text
    assert "Net 30" in text
    assert "registration number" in text


def test_small_rounding_difference_is_ignored():
    assert validate_invoice(make(total_amount=5017.21)) == []


def test_line_items_that_do_not_sum_to_subtotal():
    flags = validate_invoice(make(subtotal=4500.00, tax_amount=585.00, total_amount=5085.00))
    assert any("Line items add up to $4,440.00" in i for i in issues(flags))


def test_line_that_does_not_multiply_out():
    bad = [dict(LINES[0], total=3500.00)] + LINES[1:]
    flags = validate_invoice(make(line_items=bad, subtotal=4540.00, tax_amount=590.20, total_amount=5130.20))
    assert any("does not multiply out" in i for i in issues(flags))


def test_non_standard_tax_rate_flagged_for_canadian_invoice():
    flags = validate_invoice(make(tax_amount=444.00, total_amount=4884.00))  # 10%
    assert any("not a standard Canadian sales-tax rate" in i for i in issues(flags))


def test_standard_rates_pass():
    assert validate_invoice(make(tax_amount=222.00, total_amount=4662.00)) == []  # 5% GST


def test_us_invoice_without_registration_number_is_not_flagged():
    flags = validate_invoice(make(currency="USD", tax_registration_number=None))
    assert not any("registration" in i for i in issues(flags))


def test_registration_check_uses_document_text_when_currency_missing():
    flags = validate_invoice(make(currency=None, tax_registration_number=None), "HST (13%)  $577.20")
    assert any("registration number" in i for i in issues(flags))


def test_due_date_that_does_not_match_terms():
    flags = validate_invoice(make(due_date="2026-12-15"))
    assert any("Net 30" in i for i in issues(flags))


def test_missing_figures_are_skipped_not_guessed():
    inv = make(subtotal=None, tax_amount=None, total_amount=None, line_items=[], issue_date=None, due_date=None)
    assert validate_invoice(inv) == []


def test_numbers_are_parsed_from_strings():
    assert _num("$1,234.50") == 1234.50
    assert _num("1 234,50") == 1234.50
    assert _num("(45.00)") == -45.00
    assert _num(None) is None


def test_merge_drops_duplicates_of_model_flags_and_sorts():
    model = [
        Flag(issue="Due date (September 19, 2026) is earlier than the invoice date (October 3, 2026).",
             severity=FlagSeverity.CRITICAL, recommendation="Fix it."),
        Flag(issue="Informal handwritten approval notation.", severity=FlagSeverity.LOW, recommendation="Get sign-off."),
    ]
    ours = validate_invoice(make(total_amount=5217.20, due_date="2026-09-19"))
    merged = merge_flags(model, ours)
    # the model's date flag stands; ours is not repeated
    assert sum("before the invoice date" in f.issue or "earlier than the invoice date" in f.issue for f in merged) == 1
    # the total mismatch the model missed is added, and most severe flags come first
    assert any("does not match subtotal plus tax" in f.issue for f in merged)
    severities = [f.severity for f in merged]
    order = [FlagSeverity.CRITICAL, FlagSeverity.HIGH, FlagSeverity.MEDIUM, FlagSeverity.LOW]
    assert severities == sorted(severities, key=order.index)


def test_own_flags_do_not_suppress_each_other():
    merged = merge_flags([], validate_invoice(make(subtotal=4500.00, total_amount=5217.20)))
    text = " ".join(f.issue for f in merged)
    assert "Line items add up" in text and "does not match subtotal plus tax" in text


def test_contradicted_model_flag_is_dropped_when_line_items_add_up():
    # Seen live: the model raised "subtotal does not match the sum of line items" while its own
    # explanation said the figures matched.
    wrong = Flag(issue="Mathematical discrepancy: subtotal does not match the sum of line items",
                 severity=FlagSeverity.HIGH, recommendation="Verify.")
    other = Flag(issue="No purchase order number on the invoice", severity=FlagSeverity.LOW, recommendation="Ask.")
    kept = drop_contradicted_flags([wrong, other], make(total_amount=5217.20))
    assert kept == [other]


def test_model_total_flag_is_dropped_only_when_the_total_really_is_correct():
    claim = Flag(issue="Total due appears mathematically incorrect", severity=FlagSeverity.CRITICAL, recommendation="Check.")
    assert drop_contradicted_flags([claim], make()) == []                          # 4,440 + 577.20 = 5,017.20
    assert drop_contradicted_flags([claim], make(total_amount=5217.20)) == [claim]  # genuinely wrong: keep


def test_real_line_item_mismatch_flag_is_kept():
    claim = Flag(issue="Subtotal does not match the sum of line items", severity=FlagSeverity.HIGH, recommendation="Check.")
    inv = make(subtotal=4500.00, tax_amount=585.00, total_amount=5085.00)
    assert drop_contradicted_flags([claim], inv) == [claim]


def test_unrelated_flags_and_missing_invoice_pass_through():
    flag = Flag(issue="Due date is earlier than the invoice date", severity=FlagSeverity.CRITICAL, recommendation="Fix.")
    assert drop_contradicted_flags([flag], make()) == [flag]
    assert drop_contradicted_flags([flag], None) == [flag]


def test_duplicate_is_replaced_by_our_flag_at_the_higher_severity():
    # Seen live: the model raised the $200 total error as High; our check says Critical.
    model = Flag(issue="Arithmetic discrepancy: line items sum to $4,440.00 and HST gives a correct total of $5,017.20, "
                       "but the invoice states $5,217.20 - a $200.00 overcharge",
                 severity=FlagSeverity.HIGH, recommendation="Request a corrected invoice.")
    merged = merge_flags([model], validate_invoice(make(total_amount=5217.20)))
    totals = [f for f in merged if "5,217.20" in f.issue]
    assert len(totals) == 1                                   # not duplicated
    assert totals[0].severity == FlagSeverity.CRITICAL        # raised
    assert "does not match subtotal plus tax" in totals[0].issue


def test_misleading_model_title_is_matched_through_its_location():
    # Seen live: title says "HST calculation" (HST was fine) and only the location mentions the total.
    model = Flag(issue="Arithmetic discrepancy in HST calculation", severity=FlagSeverity.MEDIUM,
                 location="HST line and TOTAL DUE line", recommendation="Verify the correct total with the vendor.")
    merged = merge_flags([model], validate_invoice(make(total_amount=5217.20)))
    assert [f.severity for f in merged] == [FlagSeverity.CRITICAL]
    assert "HST calculation" not in merged[0].issue


def test_merge_never_lowers_a_model_severity():
    model = Flag(issue="The total does not match: discrepancy of $0.30 on the invoice total",
                 severity=FlagSeverity.CRITICAL, recommendation="Check.")
    merged = merge_flags([model], validate_invoice(make(total_amount=5017.50)))   # small gap -> our flag is High
    assert [f.severity for f in merged if "total" in f.issue.lower()][0] == FlagSeverity.CRITICAL


def test_unrelated_model_flags_are_left_alone():
    po = Flag(issue="No purchase order or reference number on the invoice", severity=FlagSeverity.LOW,
              location="Invoice header", recommendation="Include a PO to facilitate matching against procurement records.")
    merged = merge_flags([po], validate_invoice(make(total_amount=5217.20)))
    assert po in merged and len(merged) == 2
