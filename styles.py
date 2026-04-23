"""
styles.py — CSS kustom untuk Streamlit: full page, minimal padding, tampilan profesional
"""

CSS = """
<style>
/* ── FULL PAGE — hapus semua padding default Streamlit ── */
.block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    padding-top: 0.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
}

/* Sembunyikan header Streamlit default (hamburger menu area) */
header[data-testid="stHeader"] {
    height: 0px !important;
    min-height: 0px !important;
    display: none !important;
}

/* Sembunyikan footer "Made with Streamlit" */
footer { display: none !important; }

/* Sembunyikan toolbar kanan atas (record screen, dll) */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── FONT & BASE ── */
html, body, [class*="css"] {
    font-family: Arial, sans-serif;
    font-size: 13px;
}

/* ── HEADER ── */
.app-header {
    background: #1a56db;
    color: white;
    padding: 0 20px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0;
    margin-left: -1rem;
    margin-right: -1rem;
    margin-top: -0.5rem;
}
.app-header h1 {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin: 0;
}
.app-header .subtitle {
    font-size: 12px;
    color: rgba(255,255,255,0.8);
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: #1245b5;
    padding: 4px 8px 0;
    gap: 2px;
    margin-left: -1rem;
    margin-right: -1rem;
    padding-left: 12px;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.7);
    font-weight: 600;
    font-size: 12px;
    padding: 8px 14px;
    border-bottom: 3px solid transparent;
    white-space: nowrap;
}
.stTabs [aria-selected="true"] {
    color: white !important;
    border-bottom: 3px solid #60a5fa !important;
    background: rgba(255,255,255,0.1) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding: 10px 0 0;
}

/* ── METRIC CARDS ── */
.metric-card {
    border-radius: 8px;
    padding: 10px 16px;
    color: white;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    margin-bottom: 8px;
}
.metric-card .val {
    font-size: 22px;
    font-weight: 800;
    line-height: 1.1;
}
.metric-card .lbl {
    font-size: 10px;
    opacity: 0.9;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-top: 2px;
}

/* ── BADGES ── */
.badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.5;
}
.badge-blue   { background: #dbeafe; color: #1d4ed8; }
.badge-green  { background: #d1fae5; color: #059669; }
.badge-red    { background: #fee2e2; color: #dc2626; }
.badge-amber  { background: #fef3c7; color: #d97706; }
.badge-purple { background: #ede9fe; color: #6d28d9; }
.badge-teal   { background: #cffafe; color: #0e7490; }

/* ── STATUS TRACKING ── */
.trk-status {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
}
.trk-s-noPR      { background: #fee2e2; color: #dc2626; }
.trk-s-prCreated { background: #fef3c7; color: #d97706; }
.trk-s-poCreated { background: #dbeafe; color: #1d4ed8; }
.trk-s-partial   { background: #ffedd5; color: #ea580c; }
.trk-s-complete  { background: #d1fae5; color: #059669; }

/* ── INFO BAR ── */
.info-bar {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    color: #1e40af;
    margin-bottom: 8px;
}

/* ── AUDIT DIFF ── */
.audit-old {
    display: inline-block;
    background: #fee2e2;
    color: #dc2626;
    padding: 1px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-family: monospace;
    text-decoration: line-through;
}
.audit-new {
    display: inline-block;
    background: #dcfce7;
    color: #16a34a;
    padding: 1px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-family: monospace;
    font-weight: 700;
}

/* ── STREAMLIT OVERRIDES ── */
.stDataFrame { border: 1px solid #e5e7eb; border-radius: 4px; }

/* Sidebar hidden by default */
div[data-testid="stSidebar"] { display: none !important; }
div[data-testid="collapsedControl"] { display: none !important; }

/* Button styling */
.stButton > button {
    border-radius: 3px;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 14px;
}

/* Label styling */
.stSelectbox label, .stTextInput label,
.stNumberInput label, .stFileUploader label {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
}

/* ── FILTER BAR ── */
.filter-bar {
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 14px;
    margin-bottom: 8px;
}

/* ── DATAFRAME full width ── */
[data-testid="stDataFrame"] {
    width: 100% !important;
}

/* ── REMOVE TOP PADDING dari tiap elemen ── */
div[data-testid="stVerticalBlock"] > div:first-child {
    padding-top: 0 !important;
}

/* ── UPLOAD ZONE ── */
.upload-info {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 12px;
    color: #1e40af;
    margin-bottom: 12px;
}

/* Reduce gap antar elemen */
.element-container { margin-bottom: 0.25rem !important; }
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def card(val, label, color="#1a56db"):
    return f"""
    <div class="metric-card" style="background:{color};">
        <div class="val">{val}</div>
        <div class="lbl">{label}</div>
    </div>"""


def badge(text, color="blue"):
    if not text:
        return '<span style="color:#d1d5db">—</span>'
    return f'<span class="badge badge-{color}">{text}</span>'


def status_label(status):
    MAP = {
        "no-pr":      ("🔴", "Belum PR",        "trk-s-noPR"),
        "pr-created": ("🟡", "PR Created",       "trk-s-prCreated"),
        "po-created": ("🔵", "PO Created",       "trk-s-poCreated"),
        "partial":    ("🟠", "Partial Delivery", "trk-s-partial"),
        "complete":   ("✅", "Complete",          "trk-s-complete"),
    }
    ico, lbl, cls = MAP.get(status, ("❓", "Unknown", "badge-blue"))
    return f'<span class="trk-status {cls}">{ico} {lbl}</span>'


def info_bar(items: list):
    """items = [(label, value), ...]"""
    parts = []
    for label, value in items:
        parts.append(f"<span>{label}: <b>{value}</b></span>")
    content = ' <span style="color:#bfdbfe;margin:0 8px">|</span> '.join(parts)
    return f'<div class="info-bar">{content}</div>'