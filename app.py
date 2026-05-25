import streamlit as st
import os
import json
import streamlit.components.v1 as components
from dotenv import load_dotenv
from agent.processor import process_document
from agent.retry_queue import get_all_jobs, get_job_result
from models.schemas import ProcessingStatus, FlagSeverity, DocumentType
from styles import (
    GLOBAL_CSS, TOPBAR_HTML, UPLOAD_HERO_HTML, CAPABILITY_CARDS_HTML,
    SUPPORTED_CHIPS_HTML, file_banner_html, flag_card_html,
    total_block_html, field_row_html, recent_doc_row_html
)
from health import start_health_server
if "health_server_started" not in st.session_state:
    start_health_server()
    st.session_state["health_server_started"] = True

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocAgent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Inject global CSS ─────────────────────────────────────────────────────────
st.markdown(TOPBAR_HTML, unsafe_allow_html=True)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:4px;">
            <div style="width:26px;height:26px;background:#1D9E75;border-radius:6px;
                display:flex;align-items:center;justify-content:center;
                color:#E1F5EE;font-size:14px;">📄</div>
            <span style="font-size:15px;font-weight:500;">DocAgent</span>
        </div>
        <div style="font-size:12px;color:#999;margin-bottom:16px;">
            AI document intelligence
        </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:10px;font-weight:500;color:#aaa;'
        'letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px;">'
        'Settings</div>',
        unsafe_allow_html=True
    )
    show_raw_json = st.checkbox("Show raw JSON output", value=False)
    show_queue    = st.checkbox("Show processing queue", value=False)
    max_retries   = 3

    st.divider()

    # ── Recent documents ──────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:10px;font-weight:500;color:#aaa;'
        'letter-spacing:.08em;text-transform:uppercase;margin-bottom:6px;">'
        'Recent</div>',
        unsafe_allow_html=True
    )

    jobs = get_all_jobs(limit=5)
    if jobs:
        for job in jobs:
            if job["status"] != "success":
                continue

            flag_count = 0
            if job.get("result_json"):
                parsed = json.loads(job["result_json"])
                flag_count = len(parsed.get("flags", []))

            has_flags    = flag_count > 0
            badge_color  = "#FAEEDA;color:#633806" if has_flags else "#EAF3DE;color:#27500A"
            badge_label  = f"{flag_count} flags" if has_flags else "Clean"
            name         = job["filename"][:20] + "..." if len(job["filename"]) > 20 else job["filename"]
            is_active    = st.session_state.get("active_job_id") == job["id"]

            col_name, col_badge = st.columns([3, 1])

            with col_name:
                if is_active:
                    st.markdown(
                        f'<div style="background:#E1F5EE;border-radius:8px;'
                        f'padding:5px 12px;font-size:12px;font-weight:500;'
                        f'color:#085041;cursor:default;line-height:1.6;">{name}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    clicked = st.button(
                        name,
                        key=f"job_{job['id']}",
                        use_container_width=True,
                        type="secondary"
                    )
                    if clicked:
                        stored = get_job_result(job["id"])
                        if stored:
                            from models.schemas import DocumentExtraction
                            from agent.processor import ProcessingResult
                            extraction = DocumentExtraction(**stored["result"])
                            st.session_state["last_result"] = ProcessingResult(
                                status=ProcessingStatus.SUCCESS,
                                extraction=extraction,
                                job_id=job["id"],
                                file_info={
                                    "filename": stored["filename"],
                                    "size_kb":  0,
                                    "size_mb":  0
                                },
                                used_ocr=stored["result"].get("extraction_method") == "ocr",
                                processing_steps=[]
                            )
                            st.session_state["active_job_id"] = job["id"]
                            st.session_state["scroll_to_results"] = True
                            st.rerun()

            with col_badge:
                st.markdown(
                    f'<div style="font-size:10px;font-weight:500;'
                    f'border-radius:8px;padding:2px 6px;text-align:center;'
                    f'background:{badge_color};">{badge_label}</div>',
                    unsafe_allow_html=True
                )
    else:
        st.markdown(
            '<div style="font-size:12px;color:#bbb;padding:8px;">No documents yet</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── API status ────────────────────────────────────────────────────────────
    if os.getenv("ANTHROPIC_API_KEY"):
        st.markdown("""
            <div style="display:flex;align-items:center;gap:7px;">
                <div style="width:7px;height:7px;border-radius:50%;
                            background:#1D9E75;flex-shrink:0;"></div>
                <span style="font-size:11px;color:#999;">API connected</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.error("⚠ ANTHROPIC_API_KEY not set in .env")

# ── Main content ──────────────────────────────────────────────────────────────
uploaded_file = None

if "last_result" not in st.session_state:
    st.markdown(UPLOAD_HERO_HTML, unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a PDF document",
    type=["pdf"],
    help="Supports text PDFs and scanned documents (via OCR). Max 50MB.",
    label_visibility="collapsed"
)

if uploaded_file is None and "last_result" not in st.session_state:
    components.html(CAPABILITY_CARDS_HTML, height=200, scrolling=False)
    components.html(SUPPORTED_CHIPS_HTML, height=50, scrolling=False)

    jobs = get_all_jobs(limit=5)
    if jobs:
        st.markdown("""
            <div style="font-size:11px;font-weight:500;color:#aaa;
                        text-transform:uppercase;letter-spacing:.07em;
                        margin-bottom:10px;">Recently processed</div>
        """, unsafe_allow_html=True)
        for job in jobs:
            flag_count = 0
            doc_type   = "Document"
            page_count = 0
            method     = "Direct text"

            if job.get("result_json"):
                result_data = json.loads(job["result_json"])
                flag_count  = len(result_data.get("flags", []))
                doc_type    = result_data.get("document_type", "document").title()
                page_count  = result_data.get("page_count") or 0
                method      = "OCR" if result_data.get("extraction_method") == "ocr" \
                            else "Direct text"

            st.markdown(
                recent_doc_row_html(
                    filename=job["filename"],
                    doc_type=doc_type,
                    pages=page_count,
                    method=method,
                    flag_count=flag_count,
                    time_ago="-"
                ),
                unsafe_allow_html=True
            )


# ── Processing ────────────────────────────────────────────────────────────────
if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    filename   = uploaded_file.name

    st.markdown(
        file_banner_html(filename, len(file_bytes) / 1024),
        unsafe_allow_html=True
    )

    if st.button("Process document", type="primary", use_container_width=True):
        with st.status("Processing document...", expanded=True) as status_box:
            for msg in [
                "Validating file...",
                "Checking for password protection...",
                "Detecting document type...",
                "Extracting text / running OCR...",
                "Sending to Claude for analysis...",
                "Validating structured output..."
            ]:
                st.write(msg)

            result = process_document(file_bytes, filename)

            for step in result.processing_steps:
                icon = "✅" if not step["is_error"] else "❌"
                st.write(f"{icon} {step['message']}")

            if result.status == ProcessingStatus.SUCCESS:
                status_box.update(label="✅ Processing complete!", state="complete")
            else:
                status_box.update(label="❌ Processing failed", state="error")

        st.session_state["last_result"] = result
        if result.status == ProcessingStatus.SUCCESS:
            st.session_state["scroll_to_results"] = True


# ── Results ───────────────────────────────────────────────────────────────────
if "last_result" in st.session_state:

    # Anchor element — the scroll target
    st.markdown(
        '<div id="results-top" style="position:relative;top:-80px;"></div>',
        unsafe_allow_html=True
    )

    if st.session_state.pop("scroll_to_results", False):
        components.html("""
            <script>
            function scrollToResults() {
                // Try anchor scrollIntoView first
                var anchor = window.parent.document.getElementById('results-top');
                if (anchor) {
                    anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    return;
                }
                // Fallback: stMain container
                var main = window.parent.document.querySelector(
                    'section[data-testid="stMain"]'
                );
                if (main) {
                    main.scrollTo({ top: 700, behavior: 'smooth' });
                    return;
                }
                // Last resort: window
                window.parent.scrollTo({ top: 700, behavior: 'smooth' });
            }
            setTimeout(scrollToResults, 400);
            setTimeout(scrollToResults, 900);
            </script>
        """, height=1, scrolling=False)

    result = st.session_state["last_result"]

    if result.status == ProcessingStatus.SUCCESS and result.extraction:
        ext = result.extraction

        st.divider()

        # ── Metrics ───────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Document type", ext.document_type.value.title())
        m2.metric("Confidence",    f"{ext.confidence_score:.0%}")
        m3.metric(
            "Issues found",
            str(len(ext.flags)),
            delta=f"{'1 critical' if any(f.severity.value == 'critical' for f in ext.flags) else 'none critical'}",
            delta_color="off"
        )
        m4.metric(
            "Total amount",
            f"${ext.invoice_data.total_amount:,.0f}"
            if ext.invoice_data and ext.invoice_data.total_amount else "-"
        )

        st.divider()

        # ── Two column layout ─────────────────────────────────────────────────
        left, right = st.columns(2)

        with left:
            st.markdown("**Summary**")
            safe_summary = ext.summary.replace("$", r"\$").replace("_", r"\_")
            st.info(safe_summary)

            st.markdown("**Issues & flags**")

            if ext.flags:
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                sorted_flags = sorted(
                    ext.flags,
                    key=lambda f: severity_order.get(f.severity.value, 9)
                )

                all_flags_html = """
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap"
                      rel="stylesheet">
                <div style="font-family:'Inter',sans-serif;">
                """ + "".join([
                    flag_card_html(
                        severity=f.severity.value,
                        title=f.issue,
                        body=f.recommendation,
                        location=f.location
                    )
                    for f in sorted_flags
                ]) + "</div>"

                estimated_height = max(120, len(sorted_flags) * 140)
                components.html(all_flags_html, height=estimated_height, scrolling=False)

            else:
                components.html("""
                    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap"
                          rel="stylesheet">
                    <div style="font-family:'Inter',sans-serif;
                                background:#EAF3DE;border:0.5px solid #97C459;
                                border-radius:8px;padding:12px 15px;
                                font-size:13px;color:#27500A;">
                        ✅ No issues detected in this document.
                    </div>
                """, height=60, scrolling=False)

        with right:
            tab1, tab2, tab3 = st.tabs(["Extracted data", "Key fields", "File info"])

            with tab1:
                if ext.document_type in [DocumentType.INVOICE, DocumentType.RECEIPT] \
                        and ext.invoice_data:
                    inv = ext.invoice_data
                    fields = [
                        ("Invoice number", inv.invoice_number, False),
                        ("Vendor",         inv.vendor_name,    False),
                        ("Client",         inv.client_name,    False),
                        ("Issue date",     inv.issue_date,     False),
                        ("Due date",       inv.due_date,       False),
                        ("Payment terms",  inv.payment_terms,  False),
                        ("Subtotal",
                         f"${inv.subtotal:,.2f}" if inv.subtotal else "-",
                         bool(inv.subtotal and inv.total_amount and inv.tax_amount and
                              abs((inv.subtotal + (inv.tax_amount or 0)) - inv.total_amount) > 1)),
                        ("Tax",
                         f"${inv.tax_amount:,.2f}" if inv.tax_amount else "-",
                         False),
                    ]
                    for label, value, warn in fields:
                        if value:
                            st.markdown(
                                field_row_html(label, str(value), warn=warn),
                                unsafe_allow_html=True
                            )
                    if inv.total_amount:
                        st.markdown(
                            total_block_html(inv.currency or "USD", inv.total_amount),
                            unsafe_allow_html=True
                        )
                    if inv.line_items:
                        st.markdown("**Line items**")
                        st.dataframe(inv.line_items, use_container_width=True)

                elif ext.document_type in [DocumentType.CONTRACT, DocumentType.LEGAL] \
                        and ext.contract_data:
                    con = ext.contract_data
                    fields = [
                        ("Contract type",   getattr(con, "contract_type", None)),
                        ("Parties",         ", ".join(con.parties) if getattr(con, "parties", None) else None),
                        ("Effective date",  getattr(con, "effective_date", None)),
                        ("Expiration",      getattr(con, "expiration_date", None)),
                        ("Jurisdiction",    getattr(con, "jurisdiction", None)),
                        ("Governing law",   getattr(con, "governing_law", None)),
                        ("Auto-renewal",    "Yes" if getattr(con, "auto_renewal", None) is True else
                                            "No"  if getattr(con, "auto_renewal", None) is False else None),
                        ("Confidentiality", "Yes" if getattr(con, "confidentiality_clause", None) is True else
                                            "No"  if getattr(con, "confidentiality_clause", None) is False else None),
                        ("Non-compete",     "Yes" if getattr(con, "non_compete_clause", None) is True else
                                            "No"  if getattr(con, "non_compete_clause", None) is False else None),
                    ]
                    for label, value in fields:
                        if value:
                            st.markdown(
                                field_row_html(label, value),
                                unsafe_allow_html=True
                            )
                    if getattr(con, "key_obligations", None):
                        st.markdown("**Key obligations**")
                        for ob in con.key_obligations:
                            st.markdown(f"• {ob}")
                else:
                    st.markdown(
                        '<div style="font-size:13px;color:#999;padding:8px 0;">'
                        'No type-specific data available for this document.</div>',
                        unsafe_allow_html=True
                    )

            with tab2:
                if ext.raw_key_fields:
                    for k, v in ext.raw_key_fields.items():
                        st.markdown(field_row_html(k, str(v)), unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="font-size:13px;color:#999;">No additional fields.</div>',
                        unsafe_allow_html=True
                    )

            with tab3:
                if result.file_info:
                    st.markdown(field_row_html("Filename",   result.file_info["filename"]),
                                unsafe_allow_html=True)
                    st.markdown(field_row_html("File size",  f"{result.file_info['size_mb']} MB"),
                                unsafe_allow_html=True)
                st.markdown(field_row_html("Pages",           str(ext.page_count or "-")),
                            unsafe_allow_html=True)
                st.markdown(field_row_html("Words",           str(ext.word_count or "-")),
                            unsafe_allow_html=True)
                st.markdown(field_row_html("Extraction",      "OCR" if result.used_ocr else "Direct text"),
                            unsafe_allow_html=True)
                st.markdown(field_row_html("Job ID",          f"#{result.job_id}"),
                            unsafe_allow_html=True)

        # ── Raw JSON ──────────────────────────────────────────────────────────
        if show_raw_json:
            st.divider()
            st.markdown("**Raw JSON output**")
            st.json(ext.model_dump(mode="json"))

        # ── New document ──────────────────────────────────────────────────────
        st.divider()
        if st.button("Process another document", type="secondary"):
            del st.session_state["last_result"]
            st.rerun()

    elif result.status == ProcessingStatus.FAILED:
        st.error(f"**Processing failed:** {result.error_message}")
        st.markdown("""
            **Common fixes:**
            - Password-protected PDFs: remove the password before uploading
            - Corrupted files: try re-exporting the PDF from the source app
            - Scanned PDFs with poor quality: re-scan at 300 DPI minimum
            - Very large files: split into sections under 50 MB
        """)
        if st.button("Try again", type="secondary"):
            del st.session_state["last_result"]
            st.rerun()


# ── Processing queue ──────────────────────────────────────────────────────────
if show_queue:
    st.divider()
    st.markdown("**Processing queue**")
    jobs = get_all_jobs(limit=20)
    if jobs:
        display = [
            {
                "ID":       j["id"],
                "File":     j["filename"],
                "Status":   j["status"],
                "Attempts": j["attempt_count"],
                "Created":  j["created_at"][:19],
                "Error":    j["error_message"] or ""
            }
            for j in jobs
        ]
        st.dataframe(display, use_container_width=True)
    else:
        st.markdown(
            '<div style="font-size:13px;color:#999;">No jobs yet.</div>',
            unsafe_allow_html=True
        )