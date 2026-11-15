from styles import table_html


def test_line_items_render_as_html_with_money_formatting():
    html = table_html([
        {"description": "Document scanning and indexing", "quantity": 40, "unit_price": 85.0, "total": 3400.0},
        {"description": "Rush handling surcharge", "quantity": 1, "unit_price": 150.0, "total": 150.0},
    ])
    assert "<table" in html and "Unit Price" in html
    assert "$3,400.00" in html and "$85.00" in html
    assert ">40<" in html                      # quantity is not formatted as money
    assert "\n\n" not in html                  # a blank line would break Streamlit's HTML rendering


def test_text_is_escaped():
    html = table_html([{"description": "<script>alert(1)</script> & co", "total": 1.0}])
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_empty_and_odd_input_is_safe():
    assert table_html([]) == "" and table_html(None) == ""
    assert table_html(["not a dict", {"a": None, "b": True}]).count("<tr>") == 2   # header + one row
