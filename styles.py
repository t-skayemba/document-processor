# All custom CSS and HTML templates for DocAgent UI

TEAL = "#1D9E75"
TEAL_LIGHT = "#E1F5EE"
TEAL_MID = "#5DCAA5"
TEAL_DARK = "#085041"
TEAL_DARKER = "#04342C"

AMBER_LIGHT = "#FAEEDA"
AMBER_MID = "#EF9F27"
AMBER_DARK = "#633806"

CORAL_LIGHT = "#FAECE7"
CORAL_MID = "#D85A30"
CORAL_DARK = "#993C1D"

RED_LIGHT = "#FCEBEB"
RED_MID = "#F09595"
RED_DARK = "#791F1F"
RED_DARKER = "#A32D2D"

GREEN_LIGHT = "#EAF3DE"
GREEN_MID = "#639922"
GREEN_DARK = "#27500A"

GLOBAL_CSS = f"""
<style>

/* --- Reset & base --------------------------------------------------------- */
html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

/* --- 3px teal accent bar at the very top ---------------------------------- */
/* Injected as raw HTML */
.topbar-accent {{
    height: 3px;
    background: {TEAL};
    margin: -1rem -1rem 0 -1rem;
    width: calc(100% + 2rem);
}}

/* --- App background ------------------------------------------------------- */
.stApp {{
    background: #ffffff;
}}
[data-testid="stAppViewContainer"] > section:first-child {{
    background: #ffffff;
}}

/* --- Sidebar: force white ------------------------------------------------- */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {{
    background: #ffffff !important;
}}
[data-testid="stSidebar"] {{
    border-right: 0.5px solid rgba(0, 0, 0, 0.08) !important;
}}

/* --- Sidebar section headers ---------------------------------------------- */
[data-testid="stSidebar"] .sidebar-section {{
    font-size: 10px;
    font-weight: 500;
    color: #888;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 12px 8px 4px;
}}

/* Primary buttons -> teal -------------------------------------------------- */
.stButton > button[kind="primary"] {{
    background: {TEAL} !important;
    color: {TEAL_LIGHT} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 6px 16px !important;
    transition: background 0.15s !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: #0F6E56 !important;
}}

/* Secoondary buttons ------------------------------------------------------- */
.stButton > button[kind="secondary"] {{
    background: transparent !important;
    border: 0.5px solid rgba(0,0,0,0.2) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    color: #444 !important;
    transition: background 0.15s !important;
}}
.stButton > button[kind="secondary"]:hover {{
    background: #f5f5f5 !important;
}}

/* File uploader: styled as dashed upload zone ------------------------------ */
[data-testid="stFileUploader"] {{
    border: 1.5px dashed {TEAL_MID} !important;
    border-radius: 12px !important;
    background: #F7FDFB !important;
    padding: 8px !important;
    transition: border-color 0.15s, background 0.15s !important;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: {TEAL} !important;
    background: #edfaf5 !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    background: transparent !important;
    border: none !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] > div > span {{
    color: {TEAL_DARK} !important;
    font-weight: 500 !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {{
    color: #666 !important;
}}
/* The "Browse files" button inside the uploader */
[data-testid="stFileUploader"] button {{
    background: {TEAL} !important;
    color: {TEAL_LIGHT} !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}}

/* --- Metric cards: white with colored top border -------------------------- */
[data-testid="stMetric"] {{
    background: #ffffff;
    border: 0.5px solid rgba(0,0,0,0.09);
    border-top: 2px solid {TEAL};
    border-radius: 8px;
    padding: 14px 16px !important;
}}
[data-testid="stMetric"] label {{
    font-size: 11px !important;
    color: #666 !important;
    font-weight: 400 !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-size: 22px !important;
    font-weight: 500 !important;
    color: #111 !important;
}}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-size: 11px !important;
}}

/* -- Info/success/warning/error boxes -> match flag palette ---------------- */
[data-testid="stAlert"][data-baseweb="notification"][kind="info"] {{
    background: {TEAL_LIGHT} !important;
    border-color: {TEAL_MID} !important;
    color: {TEAL_DARK} !important;
    border-radius: 8px !important;
}}
[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {{
    background: {GREEN_LIGHT} !important;
    border-radius: 8px !important;
}}
[data-testid="stAlert"][data-baseweb="notification"][kind="error"] {{
    background: {RED_LIGHT} !important;
    border-radius: 8px !important;
}}
[data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {{
    background: {AMBER_LIGHT} !important;
    border-radius: 8px !important;
}}

/* --- st.status (processing pipeline box) ---------------------------------- */
[data-testid="stStatusWidget"] {{
    border: 0.5px solid rgba(0,0,0,0.09) !important;
    border-radius: 12px !important;
    background: #ffffff !important;
    font-size: 13px !important;
    font-family: monospace !important;
}}
/* --- Expander (used for flag details) ------------------------------------- */
[data-testid="stExpander"] {{
    border: 0.5px solid rgba(0,0,0,0.09) !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary:hover {{
    background: #f9f9f9 !important;
}}

/* --- Tabs ----------------------------------------------------------------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    border-bottom: 0.5px solid rgba(0,0,0,0.09) !important;
    gap: 0 !important;
    background: transparent !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    font-size: 13px !important;
    color: #666 !important;
    padding: 8px 16px !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    color: #111 !important;
    font-weight: 500 !important;
    border-bottom: 2px solid {TEAL} !important;
}}

/* --- Dividers ------------------------------------------------------------- */
hr {{
    border: none !important;
    border-top: 0.5px solid rgba(0,0,0,0.08) !important;
    margin: 16px 0 !important;
}}

/* Datafram / table --------------------------------------------------------- */
[data-testid="stDataFrame"] {{
    border: 0.5px solid rgba(0,0,0,0.09) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] th {{
    background: #f9f9f9 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #666 !important;
}}
[data-testid="stDataFrame"] td {{
    font-size: 12px !important;
}}

/* --- Spinner -------------------------------------------------------------- */
[data-testid="stSpinner"] > div {{
    border-top-color: {TEAL} !important;
}}

/* --- Scrollbar ------------------------------------------------------------ */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: rgba(0,0,0,0.15); border-radius: 4px; }}

/* Slider — override red default to teal */
div[data-testid="stSlider"] > div > div > div[role="slider"] {{
    background: {TEAL} !important;
    border-color: {TEAL} !important;
}}
div[data-testid="stSlider"] > div > div > div > div[data-testid="stTickBar"] {{
    background: transparent !important;
}}
/* Track fill only */
div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child > div:first-child {{
    background: {TEAL} !important;
}}

/* ── Sidebar job buttons ────────────────────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    color: #666 !important;
    text-align: left !important;
    padding: 5px 12px !important;
    width: 100% !important;
    box-shadow: none !important;
    line-height: 1.6 !important; 
    transition: background 0.1s !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: #F0FAF6 !important;
    color: #085041 !important;
}}
[data-testid="stSidebar"] .stButton > button:focus:not(:active) {{
    box-shadow: none !important;
    outline: none !important;
    border: none !important;
}}
/* Active job — teal highlight */
[data-testid="stSidebar"] .stButton > button[data-active="true"],
[data-testid="stSidebar"] .active-job button {{
    background: #E1F5EE !important;
    color: #085041 !important;
    font-weight: 500 !important;
}}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
    gap: 4px !important;
    align-items: center !important;
}}

</style>
"""

# --- Custom HTML components ------------------------------------------------------------------
# injected via st.markdown(unsafe_allow_html=True)
# for UI sections that Streamlit cannot style natively

TOPBAR_HTML = """
<div style="height:3px;background:#1D9E75;margin:-1rem -1rem 1rem -1rem;width:calc(100% + 2rem);"></div>
"""

def file_banner_html(filename: str, size_kb: float) -> str:
    return f"""
    <div style="
        background:#E1F5EE;
        border:0.5px solid #5DCAA5;
        border-radius:8px;
        padding:10px 14px;
        font-size:13px;
        color:#085041;
        display:flex;
        align-items:center;
        gap:8px;
        margin-bottom:8px;
    ">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
            stroke="#1D9E75" stroke-width="2" stroke-linecap="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19
                    a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
        </svg>
        <strong>{filename}</strong> &nbsp;·&nbsp; {size_kb:.1f} KB
    </div>
    """

def flag_card_html(severity: str, title: str, body: str, location: str = None) -> str:
    """
    Returns a styled flag card as raw HTML.
    severity: "critical" | "high" | "medium" | "low"
    """
    palette = {
        "critical": {
            "bg": "#FCEBEB", "border": "#F09595",
            "title_color": "#791F1F", "body_color": "#A32D2D",
            "pill_bg": "#F7C1C1", "pill_color": "#791F1F",
            "label": "Critical"
        },
        "high": {
            "bg": "#FAEEDA", "border": "#FAC775",
            "title_color": "#633806", "body_color": "#854F0B",
            "pill_bg": "#FAC775", "pill_color": "#412402",
            "label": "High"
        },
        "medium": {
            "bg": "#E1F5EE", "border": "#5DCAA5",
            "title_color": "#085041", "body_color": "#0F6E56",
            "pill_bg": "#9FE1CB", "pill_color": "#04342C",
            "label": "Medium"
        },
        "low": {
            "bg": "#EAF3DE", "border": "#97C459",
            "title_color": "#27500A", "body_color": "#3B6D11",
            "pill_bg": "#C0DD97", "pill_color": "#173404",
            "label": "Low"
        },
    }
    p = palette.get(severity.lower(), palette["medium"])
    location_html = (
        f'<div style="font-size:11px;color:{p["body_color"]};margin-top:3px;">'
        f'Location: {location}</div>'
    ) if location else ""

    bg         = p['bg']
    border     = p['border']
    title_color = p['title_color']
    body_color  = p['body_color']
    pill_bg    = p['pill_bg']
    pill_color = p['pill_color']
    label      = p['label']

    return f"""
    <div style="
        background:{bg};
        border:0.5px solid {border};
        border-radius:8px;
        padding:11px;
        margin-bottom:8px;
    ">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:4px;">
            <div style="font-size:13px;font-weight:500;color:{title_color};
                        line-height:1.4;flex:1;">{title}</div>
            <span style="
                font-size:10px;font-weight:500;
                background:{pill_bg};color:{pill_color};
                border-radius:10px;padding:2px 8px;flex-shrink:0;
            ">{label}</span>
        </div>
        {location_html}
        <div style="font-size:12px;color:{body_color};line-height:1.5;">
            {body}
        </div>
    </div>
    """

def total_block_html(currency: str, amount: float) -> str:
    return f"""
    <div style="
        background:#E1F5EE;
        border:0.5px solid #5DCAA5;
        border-radius:8px;
        padding:12px 15px;
        margin-top:12px;
        display:flex;
        align-items:baseline;
        justify-content:space-between;
    ">
        <span style="font-size:12px;color:#0F6E56;">Invoice total</span>
        <span style="font-size:22px;font-weight:500;color:#04342C;">
            {currency} ${amount:,.2f}
        </span>
    </div>
    """

def field_row_html(label: str, value: str, warn: bool = False) -> str:
    val_color = "#854F0B" if warn else "#111111"
    warn_icon = " ⚠" if warn else ""
    return f"""
    <div style="
        display:flex;justify-content:space-between;align-items:baseline;
        padding:7px 0;border-bottom:0.5px solid rgba(0,0,0,0.07);gap:8px;
    ">
        <span style="font-size:12px;color:#666;flex-shrink:0;">{label}</span>
        <span style="font-size:12px;font-weight:500;color:{val_color};text-align:right;">
            {value}{warn_icon}
        </span>
    </div>
    """

UPLOAD_HERO_HTML = f"""
<div style="margin-bottom:20px;">
    <div style="
        font-size:11px;font-weight:500;color:{TEAL};
        letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px;
    ">AI document intelligence</div>
    <div style="font-size:22px;font-weight:500;margin-bottom:8px;line-height:1.3;">
        Drop in a document.<br>Get answers in seconds.
    </div>
    <div style="font-size:14px;color:#555;line-height:1.65;max-width:520px;">
        Extract structured data, catch issues, and get plain-English summaries 
        from any PDF - invoices, contracts, legal filings, or financial reports.
    </div>
</div>
"""

CAPABILITY_CARDS_HTML = f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0;
            font-family:'Inter',sans-serif;">

    <div style="border:0.5px solid rgba(0,0,0,0.09);border-radius:12px;padding:15px;">
        <div style="width:30px;height:30px;background:#E1F5EE;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    margin-bottom:10px;color:#1D9E75;font-size:15px;font-weight:600;">↑</div>
        <div style="font-size:13px;font-weight:500;margin-bottom:4px;color:#111;">Structured extraction</div>
        <div style="font-size:12px;color:#666;line-height:1.5;">
            Pulls parties, dates, amounts, and clauses into clean JSON —
            ready to export or pipe into your systems.
        </div>
    </div>

    <div style="border:0.5px solid rgba(0,0,0,0.09);border-radius:12px;padding:15px;">
        <div style="width:30px;height:30px;background:#FAEEDA;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    margin-bottom:10px;color:#854F0B;font-size:15px;font-weight:600;">!</div>
        <div style="font-size:13px;font-weight:500;margin-bottom:4px;color:#111;">Issue flagging</div>
        <div style="font-size:12px;color:#666;line-height:1.5;">
            Detects math discrepancies, missing fields, risky clauses,
            and one-sided terms — ranked by severity.
        </div>
    </div>

    <div style="border:0.5px solid rgba(0,0,0,0.09);border-radius:12px;padding:15px;">
        <div style="width:30px;height:30px;background:#FAECE7;border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    margin-bottom:10px;color:#993C1D;font-size:15px;font-weight:600;">⊙</div>
        <div style="font-size:13px;font-weight:500;margin-bottom:4px;color:#111;">Scanned PDF support</div>
        <div style="font-size:12px;color:#666;line-height:1.5;">
            No text layer? OCR runs automatically on image-based PDFs —
            no manual steps needed.
        </div>
    </div>

</div>
"""

SUPPORTED_CHIPS_HTML = f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;
            margin-bottom:24px;font-family:'Inter',sans-serif;">
    <span style="font-size:11px;color:#999;margin-right:4px;">Works with</span>
    {"".join([
        f'<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 10px;'
        f'border:0.5px solid rgba(0,0,0,0.1);border-radius:12px;font-size:11px;color:#555;">'
        f'{chip}</span>'
        for chip in ["Invoices", "Contracts", "Legal docs", "Financial reports", "Receipts"]
    ])}
</div>
"""

def recent_doc_row_html(filename: str, doc_type: str, pages: int, method: str, flag_count: int, time_ago: str) -> str:
    flag_style = (
        f"background:#FAEEDA;color:#633806;"
        if flag_count > 0 else
        f"background:#EAF3DE;color:#27500A;"
    )
    flag_label = f"{flag_count} flag{'s' if flag_count != 1 else ''}" if flag_count > 0 else "Clean"
    icon_bg = TEAL_LIGHT
    icon_color = TEAL

    return f"""
    <div style="
        display:flex;align-items:center;gap:10px;
        padding:9px 0;border-bottom:0.5px solid rgba(0,0,0,0.07);
    ">
        <div style="
            width:30px;height:30px;background:{icon_bg};border-radius:8px;
            display:flex;align-items:center;justify-content:center;
            font-size:14px;flex-shrink:0;color:{icon_color};font-weight:500;
        ">📄</div>
        <div style="flex:1;min-width:0;">
            <div style="font-size:13px;font-weight:500;
                        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {filename}
            </div>
            <div style="font-size:11px;color:#999;">
                {doc_type} &nbsp;·&nbsp; {pages} pages &nbsp;·&nbsp; {method}
            </div>
        </div>
        <span style="font-size:10px;font-weight:500;border-radius:10px;
                    padding:2px 8px;{flag_style}flex-shrink:0;">
            {flag_label}
        </span>
        <span style="font-size:11px;color:#bbb;flex-shrink:0;">{time_ago}</span>
    </div>
    """