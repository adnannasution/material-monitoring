"""styles.py — Design system profesional untuk PRISMA · TA-ex System"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── RESET & BASE ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', Arial, sans-serif;
    font-size: 13px;
    color: #1a1a2e;
}

/* ── HIDE STREAMLIT CHROME ── */
header[data-testid="stHeader"]      { display: none !important; }
footer                               { display: none !important; }
[data-testid="stToolbar"]           { display: none !important; }
[data-testid="stDecoration"]        { display: none !important; }
[data-testid="stMainMenu"]          { display: none !important; }
div[data-testid="stSidebar"]        { display: none !important; }
div[data-testid="collapsedControl"] { display: none !important; }
#MainMenu                           { display: none !important; }

/* ── FULL PAGE LAYOUT ── */
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}
section[data-testid="stMain"] > div {
    padding: 0 !important;
}
.element-container { margin-bottom: 0 !important; }
div[data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── TOP HEADER BAR ── */
.prisma-header {
    background: linear-gradient(135deg, #1a56db 0%, #1245b5 100%);
    color: white;
    padding: 0 24px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(26,86,219,0.3);
}
.prisma-header-left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.prisma-header-title {
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 0.3px;
}
.prisma-header-sub {
    font-size: 11px;
    color: rgba(255,255,255,0.65);
    font-weight: 400;
    margin-left: 6px;
    border-left: 1px solid rgba(255,255,255,0.3);
    padding-left: 10px;
}

/* ── TAB BAR ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0f3fa6;
    padding: 0 16px;
    gap: 0;
    border-bottom: none;
    overflow-x: auto;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.6);
    font-weight: 500;
    font-size: 12px;
    padding: 12px 16px;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    white-space: nowrap;
    transition: all 0.15s;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: rgba(255,255,255,0.9);
    background: rgba(255,255,255,0.05) !important;
}
.stTabs [aria-selected="true"] {
    color: white !important;
    border-bottom: 3px solid #60a5fa !important;
    background: rgba(255,255,255,0.08) !important;
    font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding: 0 !important;
    background: #f0f2f6;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }

/* ── FIX GAP ANTARA TAB DAN KONTEN ── */
.stTabs { gap: 0 !important; }
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
    padding: 0 !important;
}
/* Hapus margin/padding di dalam tab panel */
.stTabs [data-baseweb="tab-panel"] > div {
    padding: 0 !important;
    margin: 0 !important;
}
/* Hapus gap default semua stVerticalBlock */
section[data-testid="stMain"] .stVerticalBlock {
    gap: 0 !important;
}

/* ── PAGE CONTENT WRAPPER ── */
.page-content {
    padding: 14px 20px;
    background: #f0f2f6;
    min-height: calc(100vh - 100px);
}

/* ── CARD ── */
.card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
    overflow: hidden;
}
.card-header {
    padding: 12px 16px;
    border-bottom: 1px solid #f1f5f9;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.card-title {
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
    display: flex;
    align-items: center;
    gap: 8px;
}
.card-body { padding: 16px; }

/* ── FILTER CARD ── */
.filter-card {
    background: white;
    border-radius: 8px;
    padding: 12px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

/* ── ACTION BUTTONS ── */
.btn-primary {
    background: #1a56db;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s;
    white-space: nowrap;
}
.btn-primary:hover { background: #1245b5; box-shadow: 0 2px 8px rgba(26,86,219,0.35); }

.btn-success {
    background: #059669; color: white;
    border: none; border-radius: 6px;
    padding: 7px 16px; font-size: 12px; font-weight: 600;
    cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.btn-success:hover { background: #047857; }

.btn-outline {
    background: white; color: #374151;
    border: 1px solid #d1d5db; border-radius: 6px;
    padding: 6px 14px; font-size: 12px; font-weight: 500;
    cursor: pointer; white-space: nowrap; transition: all 0.15s;
}
.btn-outline:hover { border-color: #1a56db; color: #1a56db; background: #eff6ff; }

/* ── STAT CARDS ── */
.stat-row {
    display: flex;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
}
.stat-card {
    background: white;
    border-radius: 10px;
    padding: 14px 20px;
    min-width: 120px;
    flex: 1;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    border-left: 4px solid;
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.stat-val {
    font-size: 26px;
    font-weight: 800;
    line-height: 1;
    color: #1e293b;
}
.stat-lbl {
    font-size: 11px;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── PAGINATION ── */
.pagination-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    background: white;
    border-top: 1px solid #e2e8f0;
    border-radius: 0 0 8px 8px;
    font-size: 12px;
    color: #64748b;
}
.pagination-info { font-weight: 500; }
.pagination-info b { color: #1e293b; }

/* ── BADGES ── */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
}
.badge-blue   { background: #dbeafe; color: #1d4ed8; }
.badge-green  { background: #d1fae5; color: #065f46; }
.badge-red    { background: #fee2e2; color: #b91c1c; }
.badge-amber  { background: #fef3c7; color: #92400e; }
.badge-purple { background: #ede9fe; color: #5b21b6; }
.badge-teal   { background: #ccfbf1; color: #0f766e; }
.badge-gray   { background: #f1f5f9; color: #475569; }

/* ── STATUS TRACKING ── */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}
.status-no-pr      { background: #fee2e2; color: #b91c1c; }
.status-pr-created { background: #fef3c7; color: #92400e; }
.status-po-created { background: #dbeafe; color: #1d4ed8; }
.status-partial    { background: #ffedd5; color: #c2410c; }
.status-complete   { background: #d1fae5; color: #065f46; }

/* ── INFO BANNER ── */
.info-banner {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 12px;
    color: #1e40af;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
}
.info-banner-item { display: flex; align-items: center; gap: 5px; }
.info-banner-item b { color: #1e40af; }
.info-divider { width: 1px; height: 16px; background: #bfdbfe; }

/* ── UPLOAD HINT ── */
.upload-hint {
    background: #f8fafc;
    border: 1.5px dashed #cbd5e1;
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
    font-size: 12px;
    color: #94a3b8;
}
.upload-hint b { color: #64748b; }

/* ── SECTION TITLE ── */
.section-title {
    font-size: 15px;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── TABLE WRAPPER ── */
.table-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    overflow: hidden;
}
.table-info {
    padding: 8px 16px;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
}
.table-info b { color: #334155; }

/* ── STREAMLIT WIDGET OVERRIDES ── */
.stTextInput > div > div > input {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 12px !important;
    background: #f8fafc !important;
    transition: all 0.15s;
}
.stTextInput > div > div > input:focus {
    border-color: #1a56db !important;
    background: white !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,0.1) !important;
}
.stSelectbox > div > div {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 6px !important;
    background: #f8fafc !important;
    font-size: 12px !important;
}
.stButton > button {
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 7px 16px !important;
    transition: all 0.15s !important;
    border: 1.5px solid transparent !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#1a56db,#1d4ed8) !important;
    color: white !important;
    box-shadow: 0 2px 4px rgba(26,86,219,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg,#1245b5,#1a56db) !important;
    box-shadow: 0 4px 12px rgba(26,86,219,0.35) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="secondary"] {
    background: white !important;
    color: #374151 !important;
    border-color: #d1d5db !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #1a56db !important;
    color: #1a56db !important;
    background: #eff6ff !important;
}
.stDownloadButton > button {
    background: #059669 !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    padding: 7px 16px !important;
    box-shadow: 0 2px 4px rgba(5,150,105,0.25) !important;
}
.stDownloadButton > button:hover {
    background: #047857 !important;
    box-shadow: 0 4px 12px rgba(5,150,105,0.35) !important;
    transform: translateY(-1px);
}
.stFileUploader {
    border: 1.5px dashed #cbd5e1 !important;
    border-radius: 8px !important;
    background: #f8fafc !important;
    padding: 8px !important;
}
.stDataFrame {
    border: none !important;
    border-radius: 0 !important;
}
[data-testid="stDataFrame"] > div {
    border-radius: 0 !important;
}
div[data-testid="stDataFrameResizable"] table thead tr th {
    background: #1e293b !important;
    color: white !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    padding: 10px 12px !important;
    border-right: 1px solid rgba(255,255,255,0.1) !important;
    white-space: nowrap !important;
}
div[data-testid="stDataFrameResizable"] table tbody tr:hover td {
    background: #f0f7ff !important;
}
div[data-testid="stDataFrameResizable"] table tbody tr:nth-child(even) td {
    background: #fafbfc;
}
.stRadio > div { gap: 8px; }
.stRadio label { font-size: 12px !important; }

/* ── EXPANDER ── */
.streamlit-expanderHeader {
    background: #f8fafc !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    color: #1e293b !important;
}

/* ── ALERTS ── */
.stSuccess > div {
    border-radius: 8px !important;
    border-left: 4px solid #059669 !important;
}
.stError > div {
    border-radius: 8px !important;
    border-left: 4px solid #dc2626 !important;
}
.stWarning > div {
    border-radius: 8px !important;
    border-left: 4px solid #d97706 !important;
}
.stInfo > div {
    border-radius: 8px !important;
    border-left: 4px solid #1a56db !important;
}

/* ── SPINNER ── */
.stSpinner > div { color: #1a56db !important; }

/* ── MULTISELECT ── */
.stMultiSelect > div > div {
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 6px !important;
    background: #f8fafc !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ── LABEL HIDDEN ── */
.stTextInput label, .stSelectbox label,
.stMultiSelect label, .stFileUploader label {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    margin-bottom: 4px !important;
}
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title, subtitle="Material Reservation & PR Management"):
    import streamlit as st
    st.markdown(f"""
    <div class="prisma-header">
        <div class="prisma-header-left">
            <span style="font-size:22px">📦</span>
            <span class="prisma-header-title">{title}</span>
            <span class="prisma-header-sub">{subtitle}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_title(icon, title):
    return f'<div class="section-title">{icon} {title}</div>'


def info_banner(items: list):
    parts = []
    for i, (label, value) in enumerate(items):
        parts.append(
            f'<div class="info-banner-item">'
            f'<span style="color:#64748b">{label}:</span> <b>{value}</b>'
            f'</div>'
        )
        if i < len(items) - 1:
            parts.append('<div class="info-divider"></div>')
    return f'<div class="info-banner">{"".join(parts)}</div>'


def stat_card(val, label, color="#1a56db", border_color=None):
    bc = border_color or color
    return f"""
    <div class="stat-card" style="border-left-color:{bc}">
        <div class="stat-val" style="color:{bc}">{val}</div>
        <div class="stat-lbl">{label}</div>
    </div>"""


def table_info_bar(showing, total, extra=""):
    ext = f" &nbsp;·&nbsp; {extra}" if extra else ""
    return (
        f'<div class="table-info">'
        f'Menampilkan <b>{showing:,}</b> dari <b>{total:,}</b> baris{ext}'
        f'</div>'
    )


def badge(text, color="blue"):
    if not text or str(text).strip() in ("", "None", "nan"):
        return '<span style="color:#cbd5e1;font-size:11px">—</span>'
    return f'<span class="badge badge-{color}">{text}</span>'


def status_pill(status):
    MAP = {
        "no-pr":      ("🔴", "Belum PR",        "status-no-pr"),
        "pr-created": ("🟡", "PR Created",       "status-pr-created"),
        "po-created": ("🔵", "PO Created",       "status-po-created"),
        "partial":    ("🟠", "Partial Delivery", "status-partial"),
        "complete":   ("✅", "Complete",          "status-complete"),
    }
    ico, lbl, cls = MAP.get(status, ("⚪", "Unknown", "badge-gray"))
    return f'<span class="status-pill {cls}">{ico} {lbl}</span>'