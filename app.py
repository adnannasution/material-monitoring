"""
app.py — PRISMA · TA-ex System (Streamlit)
Jalankan: streamlit run app.py
"""
import io, random, string, traceback
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="PRISMA · TA-ex System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from styles import inject_css, page_header, section_title, info_banner, stat_card, table_info_bar, badge, status_pill
from database import migrate, query, execute, get_state, set_state
from bulk_ops import (
    bulk_replace_taex, bulk_replace_prisma, bulk_replace_pr,
    bulk_replace_po, bulk_replace_kumpulan, bulk_replace_order,
)

inject_css()

# ── DB INIT ────────────────────────────────────────────────────
if "db_migrated" not in st.session_state:
    try:
        migrate()
        st.session_state.db_migrated = True
    except Exception as e:
        st.error(f"❌ Gagal konek ke database: {e}")
        st.stop()

# ── SESSION STATE ──────────────────────────────────────────────
for _k, _v in {"kk_data": [], "kk_code": None, "summary_data": []}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def generate_kk_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def to_excel_bytes(df: pd.DataFrame, sheet_name="Sheet1") -> bytes:
    df = df.copy()
    drop_cols = [c for c in df.columns if c in ("created_at", "updated_at")]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    for col in df.columns:
        if hasattr(df[col], "dt") and getattr(df[col].dtype, "tz", None) is not None:
            df[col] = df[col].dt.tz_localize(None)
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str).replace("nan","").replace("None","")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, sheet_name=sheet_name, index=False)
    return buf.getvalue()

def load_excel(f) -> pd.DataFrame:
    if f.name.lower().endswith(".csv"):
        return pd.read_csv(f, dtype=str, keep_default_na=False)
    return pd.read_excel(f, dtype=str, keep_default_na=False)

# ── COUNT & FETCH ──────────────────────────────────────────────
@st.cache_data(ttl=5)
def count_table(t):
    r = query(f"SELECT COUNT(*) AS c FROM {t}")
    return int(r[0]["c"]) if r else 0

def get_counts():
    return {k: count_table(v) for k, v in {
        "taex":"taex_reservasi","prisma":"prisma_reservasi",
        "kumpulan":"kumpulan_summary","pr":"sap_pr","po":"sap_po","order":"work_order"
    }.items()}

@st.cache_data(ttl=10)
def fetch_taex(search="", pr_filter="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append("""(material ILIKE %s OR material_description ILIKE %s
                         OR "order" ILIKE %s OR equipment ILIKE %s
                         OR pr ILIKE %s OR reservno ILIKE %s)""")
        p = f"%{search}%"; params.extend([p]*6)
    if pr_filter:
        conds.append("pr = %s"); params.append(pr_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(
        f'SELECT * FROM taex_reservasi {where} ORDER BY id LIMIT %s OFFSET %s',
        params + [limit, offset]
    )
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=10)
def fetch_prisma(search="", order_filter="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append("""(material ILIKE %s OR material_description ILIKE %s
                         OR "order" ILIKE %s OR equipment ILIKE %s)""")
        p = f"%{search}%"; params.extend([p]*4)
    if order_filter:
        conds.append('"order" = %s'); params.append(order_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(
        f'SELECT * FROM prisma_reservasi {where} ORDER BY id LIMIT %s OFFSET %s',
        params + [limit, offset]
    )
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=10)
def fetch_sap_pr(search="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append("(pr ILIKE %s OR material ILIKE %s OR material_description ILIKE %s OR tracking_no ILIKE %s)")
        p = f"%{search}%"; params.extend([p]*4)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(f"SELECT * FROM sap_pr {where} ORDER BY id LIMIT %s OFFSET %s", params+[limit,offset])
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=10)
def fetch_sap_po(search="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append("(po ILIKE %s OR purchreq ILIKE %s OR material ILIKE %s OR short_text ILIKE %s)")
        p = f"%{search}%"; params.extend([p]*4)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(f"SELECT * FROM sap_po {where} ORDER BY id LIMIT %s OFFSET %s", params+[limit,offset])
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=10)
def fetch_kumpulan(search="", code_filter="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append("(material ILIKE %s OR material_description ILIKE %s OR code_tracking ILIKE %s)")
        p = f"%{search}%"; params.extend([p]*3)
    if code_filter:
        conds.append("code_tracking = %s"); params.append(code_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(f"SELECT * FROM kumpulan_summary {where} ORDER BY id LIMIT %s OFFSET %s", params+[limit,offset])
    return pd.DataFrame([dict(r) for r in rows])

@st.cache_data(ttl=10)
def fetch_order(search="", limit=100, offset=0):
    conds, params = [], []
    if search:
        conds.append('("order" ILIKE %s OR description ILIKE %s OR equipment ILIKE %s OR revision ILIKE %s)')
        p = f"%{search}%"; params.extend([p]*4)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows = query(f'SELECT * FROM work_order {where} ORDER BY id LIMIT %s OFFSET %s', params+[limit,offset])
    return pd.DataFrame([dict(r) for r in rows])

# ── PAGINATION ─────────────────────────────────────────────────
def pagination(key, total, page_size):
    """Render pagination bar, return (page, offset)."""
    pk = f"_pg_{key}"
    if pk not in st.session_state:
        st.session_state[pk] = 1
    total_pages = max(1, -(-total // page_size))
    page = max(1, min(st.session_state[pk], total_pages))
    st.session_state[pk] = page
    offset = (page - 1) * page_size

    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 4, 1, 1, 2])
    with c1:
        if st.button("«", key=f"{key}_first", disabled=page<=1, use_container_width=True):
            st.session_state[pk] = 1; st.rerun()
    with c2:
        if st.button("‹ Prev", key=f"{key}_prev", disabled=page<=1, use_container_width=True):
            st.session_state[pk] = page-1; st.rerun()
    with c3:
        s = offset+1; e = min(page*page_size, total)
        st.markdown(
            f'<div style="text-align:center;padding:6px 0;font-size:12px;color:#475569;">'
            f'Halaman <b style="color:#1e293b">{page}</b> / <b style="color:#1e293b">{total_pages}</b>'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;Baris <b style="color:#1e293b">{s:,}–{e:,}</b>'
            f' dari <b style="color:#1e293b">{total:,}</b></div>',
            unsafe_allow_html=True
        )
    with c4:
        if st.button("Next ›", key=f"{key}_next", disabled=page>=total_pages, use_container_width=True):
            st.session_state[pk] = page+1; st.rerun()
    with c5:
        if st.button("»", key=f"{key}_last", disabled=page>=total_pages, use_container_width=True):
            st.session_state[pk] = total_pages; st.rerun()
    with c6:
        new_pg = st.number_input(
            "Ke hal.", min_value=1, max_value=total_pages,
            value=page, step=1, key=f"{key}_jump",
            label_visibility="collapsed"
        )
        if new_pg != page:
            st.session_state[pk] = int(new_pg); st.rerun()
    return page, offset

def reset_page(key):
    st.session_state[f"_pg_{key}"] = 1

# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════
page_header("PRISMA · TA-ex System")
counts = get_counts()

# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tabs = st.tabs([
    f"📦 TA-ex  {counts['taex']:,}",
    f"📋 PRISMA  {counts['prisma']:,}",
    f"📝 Kertas Kerja  {len(st.session_state.kk_data)}",
    f"📊 Summary  {len(st.session_state.summary_data)}",
    f"🗂 Kumpulan  {counts['kumpulan']:,}",
    f"🧾 SAP PR  {counts['pr']:,}",
    f"📋 Order  {counts['order']:,}",
    f"🛒 PO  {counts['po']:,}",
    "🔍 Tracking",
    "🔎 Audit",
    "⚙ Reset",
])
(tab_taex, tab_prisma, tab_kk, tab_summary, tab_kumpulan,
 tab_pr, tab_order, tab_po, tab_tracking, tab_audit, tab_reset) = tabs

# ══════════════════════════════════════════════════════════════
# TAB 1 — TA-EX RESERVASI
# ══════════════════════════════════════════════════════════════
with tab_taex:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("📦", "TA-ex Reservasi"), unsafe_allow_html=True)

    # ── Filter + Action Row ──
    f1, f2, f3, f4, f5, f6, f7 = st.columns([4, 2, 1, 1.5, 1.5, 1.5, 0.7])
    with f1:
        taex_search = st.text_input("Cari", placeholder="🔍  Material, Order, Equipment, PR...",
                                    key="taex_search", label_visibility="collapsed")
    with f2:
        pr_vals = query('SELECT DISTINCT pr FROM taex_reservasi WHERE pr IS NOT NULL ORDER BY pr LIMIT 500')
        pr_opts = ["— Semua PR —"] + [r["pr"] for r in pr_vals]
        pr_sel = st.selectbox("PR", pr_opts, key="taex_pr_sel", label_visibility="collapsed")
        taex_pr_filter = "" if pr_sel.startswith("—") else pr_sel
    with f3:
        ps = st.selectbox("Hal", [100,200,500], key="taex_ps", label_visibility="collapsed")
    with f4:
        taex_file = st.file_uploader("Upload", type=["xlsx","xls","csv"],
                                     key="taex_upload", label_visibility="collapsed")
    with f5:
        if taex_file:
            up_mode = st.radio("Mode", ["Tambahkan","Ganti Semua"],
                               key="taex_up_mode", horizontal=True, label_visibility="collapsed")
            if st.button("✅ Import", key="taex_import", use_container_width=True, type="primary"):
                with st.spinner("⏳ Menyimpan ke database..."):
                    try:
                        df_up = load_excel(taex_file)
                        mode = "append" if "Tambahkan" in up_mode else "replace"
                        cnt = bulk_replace_taex(df_up, mode=mode)
                        st.success(f"✅ {cnt:,} baris berhasil diimport!")
                        st.cache_data.clear(); reset_page("taex"); st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}"); st.text(traceback.format_exc())
        else:
            tpl_cols = ["PlPl","Equipment","Order","Reserv.No.","Revision","Material","Itm",
                        "Material Description","Reqmt Qty","Qty_Stock","PR","Item","Qty_PR",
                        "Cost Ctrs","SLoc","Del","FIs","ICt","PG","Recipient","Unloading Point",
                        "Reqmt Date","Qty. f. avail.check","Qty Withdrawn","BUn","G/L Acct","Price","per","Crcy"]
            st.download_button("📋 Template", data=to_excel_bytes(pd.DataFrame(columns=tpl_cols),"Template TA-ex"),
                               file_name="Template_TAex.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="taex_tpl", use_container_width=True)
    with f6:
        if counts["taex"] > 0:
            df_exp = fetch_taex(search=taex_search, pr_filter=taex_pr_filter, limit=50000)
            if not df_exp.empty:
                col_map = {"id":"ID","plant":"PlPl","equipment":"Equipment","order":"Order",
                           "reservno":"Reserv.No.","revision":"Revision","material":"Material",
                           "itm":"Itm","material_description":"Material Description",
                           "qty_reqmts":"Reqmt Qty","qty_stock":"Qty_Stock","pr":"PR","item":"Item",
                           "qty_pr":"Qty_PR","cost_ctrs":"Cost Ctrs","sloc":"SLoc","del":"Del",
                           "fis":"FIs","ict":"ICt","pg":"PG","recipient":"Recipient",
                           "unloading_point":"Unloading Point","reqmts_date":"Reqmt Date",
                           "qty_f_avail_check":"Qty. f. avail.check","qty_withdrawn":"Qty Withdrawn",
                           "uom":"BUn","gl_acct":"G/L Acct","res_price":"Price","res_per":"per","res_curr":"Crcy"}
                st.download_button("📤 Export Excel",
                                   data=to_excel_bytes(df_exp.rename(columns=col_map),"TA-ex Reservasi"),
                                   file_name=f"TAex_{datetime.now():%Y%m%d}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="taex_exp", use_container_width=True)
    with f7:
        if st.button("🔄", key="taex_refresh", help="Refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("taex"); st.rerun()

    # ── Table ──
    total_taex = counts["taex"]
    if total_taex == 0:
        st.markdown("""
        <div style="background:white;border-radius:10px;padding:48px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-top:8px;">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.4">📦</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">
                Upload file Excel TA-ex untuk memulai</div>
        </div>""", unsafe_allow_html=True)
    else:
        pg, off = pagination("taex", total_taex, ps)
        df_taex = fetch_taex(search=taex_search, pr_filter=taex_pr_filter, limit=ps, offset=off)

        st.markdown(f'<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_taex), total_taex,
                    f"Filter: {taex_search}" if taex_search else ""), unsafe_allow_html=True)

        cols_show = [c for c in ["id","plant","equipment","order","reservno","revision",
                                  "material","itm","material_description","qty_reqmts","qty_stock",
                                  "pr","item","qty_pr","cost_ctrs","sloc","del","fis","ict","pg",
                                  "recipient","unloading_point","reqmts_date",
                                  "qty_f_avail_check","qty_withdrawn","uom","gl_acct",
                                  "res_price","res_per","res_curr"] if c in df_taex.columns]
        st.dataframe(
            df_taex[cols_show],
            use_container_width=True, height=480, hide_index=True,
            column_config={
                "id":                   st.column_config.NumberColumn("ID",           width="small"),
                "plant":                st.column_config.TextColumn("PlPl",           width="small"),
                "equipment":            st.column_config.TextColumn("Equipment",      width="medium"),
                "order":                st.column_config.TextColumn("Order",          width="medium"),
                "reservno":             st.column_config.TextColumn("Reserv.No.",     width="medium"),
                "revision":             st.column_config.TextColumn("Revision",       width="small"),
                "material":             st.column_config.TextColumn("Material",       width="medium"),
                "itm":                  st.column_config.TextColumn("Itm",            width="small"),
                "material_description": st.column_config.TextColumn("Material Description", width="large"),
                "qty_reqmts":           st.column_config.NumberColumn("Reqmt Qty",    width="small"),
                "qty_stock":            st.column_config.NumberColumn("Qty Stock",    width="small"),
                "pr":                   st.column_config.TextColumn("PR",             width="medium"),
                "item":                 st.column_config.TextColumn("Item",           width="small"),
                "qty_pr":               st.column_config.NumberColumn("Qty PR",       width="small"),
                "cost_ctrs":            st.column_config.TextColumn("Cost Ctrs",      width="small"),
                "sloc":                 st.column_config.TextColumn("SLoc",           width="small"),
                "del":                  st.column_config.TextColumn("Del",            width="small"),
                "fis":                  st.column_config.TextColumn("FIs",            width="small"),
                "ict":                  st.column_config.TextColumn("ICt",            width="small"),
                "pg":                   st.column_config.TextColumn("PG",             width="small"),
                "recipient":            st.column_config.TextColumn("Recipient",      width="medium"),
                "unloading_point":      st.column_config.TextColumn("Unloading Pt",   width="medium"),
                "reqmts_date":          st.column_config.TextColumn("Reqmt Date",     width="medium"),
                "qty_f_avail_check":    st.column_config.NumberColumn("Qty Avail",    width="small"),
                "qty_withdrawn":        st.column_config.NumberColumn("Qty Withdrawn",width="small"),
                "uom":                  st.column_config.TextColumn("BUn",            width="small"),
                "gl_acct":              st.column_config.TextColumn("G/L Acct",       width="medium"),
                "res_price":            st.column_config.NumberColumn("Price",         width="small"),
                "res_per":              st.column_config.NumberColumn("per",           width="small"),
                "res_curr":             st.column_config.TextColumn("Crcy",            width="small"),
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 2 — PRISMA RESERVASI
# ══════════════════════════════════════════════════════════════
with tab_prisma:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("📋", "PRISMA Reservasi"), unsafe_allow_html=True)

    # ── Filter + Action Row ──
    pf1, pf2, pf3, pf4, pf5, pf6, pf7 = st.columns([4, 2, 1, 1.5, 1.5, 1.5, 0.7])
    with pf1:
        pr_search = st.text_input("Cari", placeholder="🔍  Material, Order, Equipment...",
                                  key="pr_search", label_visibility="collapsed")
    with pf2:
        ord_vals = query('SELECT DISTINCT "order" FROM prisma_reservasi WHERE "order" IS NOT NULL ORDER BY "order" LIMIT 1000')
        ord_opts = ["— Semua Order —"] + [r["order"] for r in ord_vals]
        ord_sel = st.selectbox("Order", ord_opts, key="pr_ord_sel", label_visibility="collapsed")
        pr_ord_filter = "" if ord_sel.startswith("—") else ord_sel
    with pf3:
        pr_ps = st.selectbox("Hal", [100,200,500], key="pr_ps", label_visibility="collapsed")
    with pf4:
        if st.button("🔄 Sinkron TA-ex", key="sync_btn", use_container_width=True, type="primary"):
            with st.spinner("⏳ Sinkronisasi data..."):
                try:
                    all_taex = query("""
                        SELECT * FROM taex_reservasi
                        WHERE UPPER(ict)='L'
                          AND (del IS NULL OR UPPER(del)!='X')
                          AND (fis IS NULL OR UPPER(fis)!='X')
                    """)
                    exist_set = {(r["order"],r["material"],r["itm"])
                                 for r in query('SELECT "order",material,itm FROM prisma_reservasi')}
                    new_rows = [t for t in all_taex if (t["order"],t["material"],t["itm"]) not in exist_set]
                    if new_rows:
                        from psycopg2.extras import execute_values
                        from database import get_conn, release_conn
                        conn = get_conn()
                        try:
                            with conn.cursor() as cur:
                                execute_values(cur, """
                                    INSERT INTO prisma_reservasi
                                    (plant,equipment,revision,"order",reservno,itm,material,
                                     material_description,del,fis,ict,pg,recipient,unloading_point,
                                     reqmts_date,qty_reqmts,uom)
                                    VALUES %s
                                """, [(t["plant"],t["equipment"],t["revision"],t["order"],
                                       t["reservno"],t["itm"],t["material"],t["material_description"],
                                       t["del"],t["fis"],t["ict"],t["pg"],t["recipient"],
                                       t["unloading_point"],t["reqmts_date"],t["qty_reqmts"],t["uom"])
                                      for t in new_rows])
                            conn.commit()
                        finally:
                            release_conn(conn)
                    skip = len(all_taex)-len(new_rows)
                    st.success(f"✅ {len(new_rows):,} baru · {skip:,} sudah ada")
                    st.cache_data.clear(); reset_page("prisma"); st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
    with pf5:
        if st.button("📝 Kertas Kerja", key="open_kk", use_container_width=True):
            st.session_state["show_kk"] = True
    with pf6:
        df_pr_exp = fetch_prisma(search=pr_search, order_filter=pr_ord_filter, limit=50000)
        if not df_pr_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_pr_exp,"PRISMA Reservasi"),
                               file_name=f"PRISMA_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="pr_exp", use_container_width=True)
    with pf7:
        if st.button("🔄", key="pr_refresh", help="Refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("prisma"); st.rerun()

    # ── Form Kertas Kerja ──
    if st.session_state.get("show_kk"):
        with st.expander("📝 Buat Kertas Kerja", expanded=True):
            kc1, kc2 = st.columns([1,2])
            with kc1:
                kk_code_new = generate_kk_code()
                st.text_input("Kode KK", value=kk_code_new, disabled=True, key="kk_code_disp")
            with kc2:
                pg_type = st.selectbox("Planner Group",
                    ["","TA (PG akhiran T)","OH (PG akhiran O)","Rutin (PG akhiran R)","All (Semua PG)"],
                    key="kk_pg")
            if pg_type:
                used = {r["order"] for r in query(
                    'SELECT DISTINCT "order" FROM prisma_reservasi WHERE code_kertas_kerja IS NOT NULL')}
                rows_pg = query('SELECT DISTINCT "order",pg FROM prisma_reservasi WHERE code_kertas_kerja IS NULL')
                def pg_match(pv, pt):
                    if not pv: return False
                    pv = str(pv).strip().upper()
                    if "TA" in pt: return pv.endswith("T")
                    if "OH" in pt: return pv.endswith("O")
                    if "Rutin" in pt: return pv.endswith("R")
                    return True
                avail = sorted({r["order"] for r in rows_pg
                                if r["order"] not in used and pg_match(r["pg"], pg_type)})
                if avail:
                    ka, kb = st.columns(2)
                    if ka.button("✅ Pilih Semua", key="kk_all"):
                        st.session_state["kk_def"] = avail; st.rerun()
                    if kb.button("✕ Hapus Semua", key="kk_none"):
                        st.session_state["kk_def"] = []; st.rerun()
                    sel = st.multiselect(f"Work Order tersedia ({len(avail)})", avail,
                                        default=st.session_state.get("kk_def",[]),
                                        key="kk_wo_sel")
                    kkb1, kkb2 = st.columns([1,4])
                    if kkb1.button("✅ Buat", key="create_kk", type="primary"):
                        if not sel:
                            st.warning("Pilih minimal satu Work Order!")
                        else:
                            src = query("""SELECT * FROM prisma_reservasi
                                WHERE "order"=ANY(%s)
                                AND (del IS NULL OR UPPER(del)!='X')
                                AND (fis IS NULL OR UPPER(fis)!='X')""", (sel,))
                            if not src:
                                st.warning("Tidak ada data yang memenuhi syarat.")
                            else:
                                kk_rows = [dict(r) for r in src]
                                for row in kk_rows: row["CodeKertasKerja"] = kk_code_new
                                st.session_state.kk_data = kk_rows
                                st.session_state.kk_code = kk_code_new
                                set_state("kk_current",{"code":kk_code_new,"data":kk_rows})
                                st.success(f"✅ Kertas Kerja {kk_code_new} — {len(kk_rows):,} baris")
                                st.session_state["show_kk"] = False
                                st.session_state["kk_def"] = []
                                st.rerun()
                    if kkb2.button("Batal", key="cancel_kk"):
                        st.session_state["show_kk"] = False; st.rerun()
                else:
                    st.info("Tidak ada WO tersedia untuk Planner Group ini.")

    # ── Table ──
    total_pr = counts["prisma"]
    if total_pr == 0:
        st.markdown("""
        <div style="background:white;border-radius:10px;padding:48px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.07);margin-top:8px;">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.4">📋</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">
                Klik <b>Sinkron TA-ex</b> untuk mengambil data dari TA-ex Reservasi</div>
        </div>""", unsafe_allow_html=True)
    else:
        pg2, off2 = pagination("prisma", total_pr, pr_ps)
        df_pr = fetch_prisma(search=pr_search, order_filter=pr_ord_filter, limit=pr_ps, offset=off2)
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_pr), total_pr), unsafe_allow_html=True)
        cols_pr = [c for c in ["id","plant","equipment","revision","order","reservno","itm",
                                "material","material_description","del","fis","ict","pg",
                                "recipient","unloading_point","reqmts_date","qty_reqmts","uom",
                                "pr_prisma","item_prisma","qty_pr_prisma","qty_stock_onhand",
                                "code_kertas_kerja"] if c in df_pr.columns]
        st.dataframe(df_pr[cols_pr], use_container_width=True, height=480, hide_index=True,
            column_config={
                "id":                   st.column_config.NumberColumn("ID",           width="small"),
                "plant":                st.column_config.TextColumn("Plant",          width="small"),
                "equipment":            st.column_config.TextColumn("Equipment",      width="medium"),
                "revision":             st.column_config.TextColumn("Revision",       width="small"),
                "order":                st.column_config.TextColumn("Order",          width="medium"),
                "reservno":             st.column_config.TextColumn("Reservno",       width="medium"),
                "itm":                  st.column_config.TextColumn("Itm",            width="small"),
                "material":             st.column_config.TextColumn("Material",       width="medium"),
                "material_description": st.column_config.TextColumn("Material Description", width="large"),
                "del":                  st.column_config.TextColumn("Del",            width="small"),
                "fis":                  st.column_config.TextColumn("FIs",            width="small"),
                "ict":                  st.column_config.TextColumn("ICt",            width="small"),
                "pg":                   st.column_config.TextColumn("PG",             width="small"),
                "recipient":            st.column_config.TextColumn("Recipient",      width="medium"),
                "unloading_point":      st.column_config.TextColumn("Unloading Pt",   width="medium"),
                "reqmts_date":          st.column_config.TextColumn("Reqmts Date",    width="medium"),
                "qty_reqmts":           st.column_config.NumberColumn("Qty Reqmts",   width="small"),
                "uom":                  st.column_config.TextColumn("UoM",            width="small"),
                "pr_prisma":            st.column_config.TextColumn("PR Prisma",      width="medium"),
                "item_prisma":          st.column_config.TextColumn("Item",           width="small"),
                "qty_pr_prisma":        st.column_config.NumberColumn("Qty PR",       width="small"),
                "qty_stock_onhand":     st.column_config.NumberColumn("Qty Stock",    width="small"),
                "code_kertas_kerja":    st.column_config.TextColumn("Code KK",        width="medium"),
            })
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 3 — KERTAS KERJA
# ══════════════════════════════════════════════════════════════
with tab_kk:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    if not st.session_state.kk_data:
        saved = get_state("kk_current")
        if saved and isinstance(saved, dict):
            st.session_state.kk_data = saved.get("data",[])
            st.session_state.kk_code = saved.get("code")

    kk_data = st.session_state.kk_data
    kk_code = st.session_state.kk_code

    st.markdown(section_title("📝", "Kertas Kerja"), unsafe_allow_html=True)
    if kk_data:
        st.markdown(info_banner([
            ("Kode KK", f"<b style='color:#5b21b6'>{kk_code or '—'}</b>"),
            ("Total Baris", f"{len(kk_data):,}"),
            ("Material Unik", f"{len({r.get('material') for r in kk_data}):,}"),
        ]), unsafe_allow_html=True)

        kk_search = st.text_input("Cari", placeholder="🔍  Material, deskripsi...",
                                  key="kk_search", label_visibility="collapsed")
        df_kk = pd.DataFrame(kk_data)
        if kk_search:
            df_kk = df_kk[df_kk.apply(lambda r: any(kk_search.lower() in str(v).lower() for v in r), axis=1)]

        cols_kk = [c for c in ["plant","equipment","revision","order","reservno","itm",
                                "material","material_description","qty_reqmts","qty_stock_onhand",
                                "code_kertas_kerja"] if c in df_kk.columns]
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_kk), len(kk_data)), unsafe_allow_html=True)
        edited = st.data_editor(df_kk[cols_kk], use_container_width=True, height=400,
                                hide_index=True,
                                column_config={"qty_stock_onhand": st.column_config.NumberColumn("Qty Stock Onhand")},
                                disabled=[c for c in cols_kk if c!="qty_stock_onhand"],
                                key="kk_editor")
        st.markdown('</div>', unsafe_allow_html=True)
        if "qty_stock_onhand" in edited.columns:
            for i, row in edited.iterrows():
                if i < len(st.session_state.kk_data):
                    st.session_state.kk_data[i]["qty_stock_onhand"] = row.get("qty_stock_onhand")

        b1, b2 = st.columns([2,6])
        if b1.button("✅ Submit Kertas Kerja", type="primary", use_container_width=True):
            summary_map = {}
            for r in st.session_state.kk_data:
                mat = r.get("material")
                if not mat: continue
                if mat not in summary_map:
                    summary_map[mat] = {"Plant":r.get("plant"),"Material":mat,
                        "Material_Description":r.get("material_description"),
                        "Qty_Req":0,"Qty_Stock":0,"CodeTracking":kk_code,
                        "Order":r.get("order"),"Equipment":r.get("equipment"),
                        "Revision":r.get("revision"),"Reservno":r.get("reservno"),"Itm":r.get("itm")}
                summary_map[mat]["Qty_Req"] += float(r.get("qty_reqmts") or 0)
                summary_map[mat]["Qty_Stock"] += float(r.get("qty_stock_onhand") or 0)
            sum_rows = [{**r,"Qty_To_PR":max(0,r["Qty_Req"]-r["Qty_Stock"])} for r in summary_map.values()]
            st.session_state.summary_data = sum_rows
            from database import get_conn, release_conn
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    for r in st.session_state.kk_data:
                        cur.execute("""UPDATE prisma_reservasi
                            SET code_kertas_kerja=%s,qty_stock_onhand=%s,updated_at=NOW()
                            WHERE "order"=%s AND material=%s AND itm=%s""",
                            (kk_code,r.get("qty_stock_onhand"),r.get("order"),r.get("material"),r.get("itm")))
                conn.commit()
            finally:
                release_conn(conn)
            set_state("summary_current", sum_rows)
            set_state("kk_current",{"code":None,"data":[]})
            st.session_state.kk_data = []
            st.success(f"✅ Submit selesai! {len(sum_rows)} material dalam Summary.")
            st.cache_data.clear(); st.rerun()
    else:
        st.markdown("""
        <div style="background:white;border-radius:10px;padding:48px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.4">📝</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada Kertas Kerja aktif</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">
                Buat dari tab <b>PRISMA Reservasi</b> → tombol <b>Kertas Kerja</b></div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 4 — SUMMARY
# ══════════════════════════════════════════════════════════════
with tab_summary:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    if not st.session_state.summary_data:
        saved_s = get_state("summary_current")
        if saved_s: st.session_state.summary_data = saved_s

    sum_data = st.session_state.summary_data
    st.markdown(section_title("📊", "Summary"), unsafe_allow_html=True)

    if sum_data:
        total_qr = sum(float(r.get("Qty_Req") or 0) for r in sum_data)
        total_qs = sum(float(r.get("Qty_Stock") or 0) for r in sum_data)
        st.markdown(info_banner([
            ("Kode KK", st.session_state.kk_code or "—"),
            ("Material Unik", f"{len(sum_data):,}"),
            ("Total Qty Req", f"{total_qr:,.0f}"),
            ("Total Qty Stock", f"{total_qs:,.0f}"),
        ]), unsafe_allow_html=True)

        sum_search = st.text_input("Cari", placeholder="🔍  Material, deskripsi...",
                                   key="sum_search", label_visibility="collapsed")
        df_sum = pd.DataFrame(sum_data)
        if sum_search:
            df_sum = df_sum[df_sum.apply(lambda r: any(sum_search.lower() in str(v).lower() for v in r), axis=1)]

        cols_sum = [c for c in ["Plant","Material","Material_Description","Qty_Req","Qty_Stock","Qty_To_PR","CodeTracking"] if c in df_sum.columns]
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_sum), len(sum_data)), unsafe_allow_html=True)
        st.dataframe(df_sum[cols_sum], use_container_width=True, height=380, hide_index=True,
            column_config={
                "Qty_Req":   st.column_config.NumberColumn("Qty Req"),
                "Qty_Stock": st.column_config.NumberColumn("Qty Stock"),
                "Qty_To_PR": st.column_config.NumberColumn("Qty to PR"),
            })
        st.markdown('</div>', unsafe_allow_html=True)

        sb1, sb2 = st.columns([2,6])
        if sb1.button("✅ Submit ke Kumpulan Summary", type="primary", use_container_width=True):
            curr_code = st.session_state.kk_code or (sum_data[0].get("CodeTracking") if sum_data else None)
            if curr_code:
                execute("DELETE FROM kumpulan_summary WHERE code_tracking=%s", (curr_code,))
            bulk_replace_kumpulan(pd.DataFrame(sum_data))
            set_state("summary_current",[])
            st.session_state.summary_data = []
            st.session_state.kk_code = None
            st.success("✅ Summary tersimpan di Kumpulan Summary!")
            st.cache_data.clear(); st.rerun()
        with sb2:
            st.download_button("📤 Export Excel", data=to_excel_bytes(pd.DataFrame(sum_data),"Summary"),
                               file_name=f"Summary_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="sum_exp")
    else:
        st.markdown("""
        <div style="background:white;border-radius:10px;padding:48px;text-align:center;
                    box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;margin-bottom:12px;opacity:0.4">📊</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data Summary</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Submit Kertas Kerja terlebih dahulu</div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 5 — KUMPULAN SUMMARY
# ══════════════════════════════════════════════════════════════
with tab_kumpulan:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("🗂", "Kumpulan Summary"), unsafe_allow_html=True)

    kf1, kf2, kf3, kf4, kf5, kf6 = st.columns([4, 2, 1, 1.5, 1.5, 0.7])
    with kf1:
        ks_search = st.text_input("Cari", placeholder="🔍  Material, code tracking...",
                                  key="ks_search", label_visibility="collapsed")
    with kf2:
        code_vals = query("SELECT DISTINCT code_tracking FROM kumpulan_summary WHERE code_tracking IS NOT NULL ORDER BY code_tracking")
        code_opts = ["— Semua Code —"] + [r["code_tracking"] for r in code_vals]
        code_sel = st.selectbox("Code", code_opts, key="ks_code_sel", label_visibility="collapsed")
        ks_code_filter = "" if code_sel.startswith("—") else code_sel
    with kf3:
        ks_ps = st.selectbox("Hal", [100,200,500], key="ks_ps", label_visibility="collapsed")
    with kf4:
        if st.button("🔄 Sinkron PR", key="pr_sync_open", use_container_width=True, type="primary"):
            st.session_state["show_pr_sync"] = True
    with kf5:
        df_ks_exp = fetch_kumpulan(limit=50000)
        if not df_ks_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_ks_exp,"Kumpulan Summary"),
                               file_name=f"Kumpulan_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="ks_exp", use_container_width=True)
    with kf6:
        if st.button("🔄", key="ks_refresh", help="Refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("ks"); st.rerun()

    if st.session_state.get("show_pr_sync"):
        with st.expander("🔄 Sinkronisasi PR dari SAP PR", expanded=True):
            kumpulan_rows = query("SELECT * FROM kumpulan_summary")
            pr_rows = query("SELECT * FROM sap_pr")
            matched = []
            for k in kumpulan_rows:
                pr_item = next((p for p in pr_rows if p["material"]==k["material"]
                    and (p["tracking_no"]==k["code_tracking"] or p["tracking"]==k["code_tracking"])), None)
                if pr_item:
                    matched.append({"Material":k["material"],"Deskripsi":k["material_description"],
                                    "PR":pr_item["pr"],"Qty_PR":pr_item["qty_pr"],"Tracking":k["code_tracking"]})
            if matched:
                st.success(f"✅ {len(matched)} material cocok")
                st.dataframe(pd.DataFrame(matched), use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Tidak ada material yang cocok antara Kumpulan Summary dan SAP PR.")
            sb1, sb2 = st.columns([1,4])
            if sb1.button("▶ Jalankan", key="run_sync", type="primary"):
                from database import get_conn, release_conn
                conn = get_conn()
                try:
                    with conn.cursor() as cur:
                        for k in kumpulan_rows:
                            pi = next((p for p in pr_rows if p["material"]==k["material"]
                                and (p["tracking_no"]==k["code_tracking"] or p["tracking"]==k["code_tracking"])), None)
                            if pi:
                                qtp = max(0, float(k["qty_req"] or 0)-float(k["qty_stock"] or 0)-float(pi["qty_pr"] or 0))
                                cur.execute("UPDATE kumpulan_summary SET qty_pr=%s,qty_to_pr=%s,updated_at=NOW() WHERE id=%s",
                                            (pi["qty_pr"],qtp,k["id"]))
                                cur.execute("""UPDATE prisma_reservasi
                                    SET pr_prisma=%s,qty_pr_prisma=%s,updated_at=NOW()
                                    WHERE material=%s AND code_kertas_kerja=%s""",
                                    (pi["pr"],pi["qty_pr"],k["material"],k["code_tracking"]))
                    conn.commit()
                finally:
                    release_conn(conn)
                st.success(f"✅ {len(matched)} material diupdate!")
                st.session_state["show_pr_sync"] = False
                st.cache_data.clear(); st.rerun()
            if sb2.button("Batal", key="cancel_sync"):
                st.session_state["show_pr_sync"] = False; st.rerun()

    ks_total = counts["kumpulan"]
    if ks_total == 0:
        st.markdown("""<div style="background:white;border-radius:10px;padding:48px;text-align:center;
            box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;opacity:0.4;margin-bottom:12px">🗂</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Submit Summary untuk mengisi Kumpulan Summary</div>
        </div>""", unsafe_allow_html=True)
    else:
        pks, oks = pagination("ks", ks_total, ks_ps)
        df_ks = fetch_kumpulan(search=ks_search, code_filter=ks_code_filter, limit=ks_ps, offset=oks)
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_ks), ks_total), unsafe_allow_html=True)
        cols_ks = [c for c in ["plant","material","material_description","qty_req","qty_stock","qty_pr","qty_to_pr","code_tracking"] if c in df_ks.columns]
        st.dataframe(df_ks[cols_ks], use_container_width=True, height=440, hide_index=True,
            column_config={
                "qty_req":    st.column_config.NumberColumn("Qty Req"),
                "qty_stock":  st.column_config.NumberColumn("Qty Stock"),
                "qty_pr":     st.column_config.NumberColumn("Qty PR"),
                "qty_to_pr":  st.column_config.NumberColumn("Qty to PR"),
            })
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 6 — SAP PR
# ══════════════════════════════════════════════════════════════
with tab_pr:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("🧾", "SAP PR — Purchase Request"), unsafe_allow_html=True)

    prf1, prf2, prf3, prf4, prf5, prf6 = st.columns([4, 1, 1.5, 1.5, 1.5, 0.7])
    with prf1:
        sap_search = st.text_input("Cari", placeholder="🔍  Material, PR, Tracking...",
                                   key="sap_search", label_visibility="collapsed")
    with prf2:
        sap_ps = st.selectbox("Hal", [100,200,500], key="sap_ps", label_visibility="collapsed")
    with prf3:
        sap_file = st.file_uploader("Upload SAP PR", type=["xlsx","xls","csv"],
                                    key="sap_upload", label_visibility="collapsed")
        if sap_file:
            if st.button("✅ Import SAP PR", key="sap_import", type="primary", use_container_width=True):
                with st.spinner("⏳ Menyimpan..."):
                    try:
                        cnt = bulk_replace_pr(load_excel(sap_file))
                        st.success(f"✅ {cnt:,} baris!")
                        st.cache_data.clear(); reset_page("sap"); st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
    with prf4:
        tpl_pr = pd.DataFrame(columns=["Plnt","Purch.Req.","Item","Material","Material Description",
                                        "D","Rel","PGr","S","TrackingNo","Qty Requested","Un",
                                        "Req.Date","Valn Price","Crcy","Per","Release Dt"])
        st.download_button("📋 Template", data=to_excel_bytes(tpl_pr,"Template SAP PR"),
                           file_name="Template_SAP_PR.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key="pr_tpl", use_container_width=True)
    with prf5:
        df_sap_exp = fetch_sap_pr(search=sap_search, limit=50000)
        if not df_sap_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_sap_exp,"SAP PR"),
                               file_name=f"SAP_PR_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="sap_exp", use_container_width=True)
    with prf6:
        if st.button("🔄", key="sap_refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("sap"); st.rerun()

    sap_total = counts["pr"]
    if sap_total == 0:
        st.markdown("""<div style="background:white;border-radius:10px;padding:48px;text-align:center;
            box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;opacity:0.4;margin-bottom:12px">🧾</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data SAP PR</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Upload file Excel SAP PR untuk memulai</div>
        </div>""", unsafe_allow_html=True)
    else:
        psap, osap = pagination("sap", sap_total, sap_ps)
        df_sap = fetch_sap_pr(search=sap_search, limit=sap_ps, offset=osap)
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_sap), sap_total), unsafe_allow_html=True)
        cols_sap = [c for c in ["id","plant","pr","item","material","material_description",
                                 "d","r","pgr","s","tracking_no","qty_pr","un","req_date",
                                 "valn_price","pr_curr","pr_per","release_date"] if c in df_sap.columns]
        st.dataframe(df_sap[cols_sap], use_container_width=True, height=440, hide_index=True,
            column_config={
                "id":   st.column_config.NumberColumn("ID", width="small"),
                "qty_pr": st.column_config.NumberColumn("Qty Requested"),
                "valn_price": st.column_config.NumberColumn("Valn Price"),
            })
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 7 — ORDER
# ══════════════════════════════════════════════════════════════
with tab_order:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("📋", "Work Order"), unsafe_allow_html=True)

    of1, of2, of3, of4, of5 = st.columns([4, 1, 1.5, 1.5, 0.7])
    with of1:
        ord_search = st.text_input("Cari", placeholder="🔍  Order, deskripsi, equipment...",
                                   key="ord_search", label_visibility="collapsed")
    with of2:
        ord_ps = st.selectbox("Hal", [100,200,500], key="ord_ps", label_visibility="collapsed")
    with of3:
        ord_file = st.file_uploader("Upload Order", type=["xlsx","xls","csv"],
                                    key="ord_upload", label_visibility="collapsed")
        if ord_file:
            if st.button("✅ Import Order", key="ord_import", type="primary", use_container_width=True):
                with st.spinner("⏳ Menyimpan..."):
                    try:
                        cnt = bulk_replace_order(load_excel(ord_file))
                        st.success(f"✅ {cnt:,} baris!")
                        st.cache_data.clear(); reset_page("ord"); st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
    with of4:
        df_ord_exp = fetch_order(search=ord_search, limit=50000)
        if not df_ord_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_ord_exp,"Order"),
                               file_name=f"Order_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="ord_exp", use_container_width=True)
    with of5:
        if st.button("🔄", key="ord_refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("ord"); st.rerun()

    ord_total = counts["order"]
    if ord_total == 0:
        st.markdown("""<div style="background:white;border-radius:10px;padding:48px;text-align:center;
            box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;opacity:0.4;margin-bottom:12px">📋</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data Order</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Upload file Excel Work Order untuk memulai</div>
        </div>""", unsafe_allow_html=True)
    else:
        pord, oord = pagination("ord", ord_total, ord_ps)
        df_ord = fetch_order(search=ord_search, limit=ord_ps, offset=oord)
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_ord), ord_total), unsafe_allow_html=True)
        cols_ord = [c for c in ["plant","order","superior_order","notification","created_on",
                                 "description","revision","equipment","system_status","user_status",
                                 "funct_location","location","wbs_ord_header","cost_center",
                                 "total_plan_cost","total_act_cost","planner_group","main_work_ctr",
                                 "entry_by","changed_by","basic_start_date","basic_finish_date","actual_release"]
                    if c in df_ord.columns]
        st.dataframe(df_ord[cols_ord], use_container_width=True, height=440, hide_index=True,
            column_config={
                "total_plan_cost": st.column_config.NumberColumn("Total Plan Cost"),
                "total_act_cost":  st.column_config.NumberColumn("Total Act. Cost"),
            })
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 8 — PO
# ══════════════════════════════════════════════════════════════
with tab_po:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("🛒", "Purchase Order (PO)"), unsafe_allow_html=True)

    pof1, pof2, pof3, pof4, pof5 = st.columns([4, 1, 1.5, 1.5, 0.7])
    with pof1:
        po_search = st.text_input("Cari", placeholder="🔍  PO, Purchreq, Material...",
                                  key="po_search", label_visibility="collapsed")
    with pof2:
        po_ps = st.selectbox("Hal", [100,200,500], key="po_ps", label_visibility="collapsed")
    with pof3:
        po_file = st.file_uploader("Upload PO", type=["xlsx","xls","csv"],
                                   key="po_upload", label_visibility="collapsed")
        if po_file:
            if st.button("✅ Import PO", key="po_import", type="primary", use_container_width=True):
                with st.spinner("⏳ Menyimpan..."):
                    try:
                        cnt = bulk_replace_po(load_excel(po_file))
                        st.success(f"✅ {cnt:,} baris!")
                        st.cache_data.clear(); reset_page("po"); st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")
    with pof4:
        df_po_exp = fetch_sap_po(search=po_search, limit=50000)
        if not df_po_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_po_exp,"PO"),
                               file_name=f"PO_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="po_exp", use_container_width=True)
    with pof5:
        if st.button("🔄", key="po_refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("po"); st.rerun()

    po_total = counts["po"]
    if po_total == 0:
        st.markdown("""<div style="background:white;border-radius:10px;padding:48px;text-align:center;
            box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;opacity:0.4;margin-bottom:12px">🛒</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Belum ada data PO</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Upload file Excel PO untuk memulai</div>
        </div>""", unsafe_allow_html=True)
    else:
        ppo, opo = pagination("po", po_total, po_ps)
        df_po = fetch_sap_po(search=po_search, limit=po_ps, offset=opo)
        st.markdown('<div class="table-card">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_po), po_total), unsafe_allow_html=True)
        cols_po = [c for c in ["plnt","purchreq","item","material","short_text","po","po_item",
                                "d","dci","pgr","doc_date","po_quantity","qty_delivered",
                                "deliv_date","oun","net_price","crcy","per"] if c in df_po.columns]
        st.dataframe(df_po[cols_po], use_container_width=True, height=440, hide_index=True,
            column_config={
                "po_quantity":    st.column_config.NumberColumn("PO Qty"),
                "qty_delivered":  st.column_config.NumberColumn("Qty Delivered"),
                "net_price":      st.column_config.NumberColumn("Net Price"),
            })
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 9 — TRACKING
# ══════════════════════════════════════════════════════════════
with tab_tracking:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("🔍", "End-to-End Procurement Tracking"), unsafe_allow_html=True)

    tf1, tf2, tf3, tf4 = st.columns([4, 2, 2, 1])
    with tf1:
        trk_search = st.text_input("Cari", placeholder="🔍  Order, Material, PR, PO...",
                                   key="trk_search", label_visibility="collapsed")
    with tf2:
        trk_status = st.selectbox("Status", ["— Semua Status —",
            "🔴 Belum PR","🟡 PR Created","🔵 PO Created","🟠 Partial Delivery","✅ Complete"],
            key="trk_status", label_visibility="collapsed")
    with tf3:
        trk_ps = st.selectbox("Hal", [100,200,500], key="trk_ps", label_visibility="collapsed")
    with tf4:
        if st.button("🔄", key="trk_refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("trk"); st.rerun()

    @st.cache_data(ttl=15)
    def build_tracking(search="", limit=200, offset=0):
        conds, params = [], []
        if search:
            conds.append("""(t.material ILIKE %s OR t.material_description ILIKE %s
                             OR t."order" ILIKE %s OR t.pr ILIKE %s)""")
            p = f"%{search}%"; params.extend([p]*4)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        sql = f"""
            SELECT t.plant, t.equipment, t."order", t.reservno, t.revision,
                   t.material, t.itm, t.material_description,
                   t.qty_reqmts, t.qty_stock, t.pr, t.item AS pr_item, t.qty_pr,
                   t.del, t.fis, t.ict, t.pg, t.cost_ctrs,
                   wo.description, wo.system_status, wo.planner_group,
                   wo.basic_start_date, wo.basic_finish_date,
                   sp.req_date,
                   po.po AS po_num, po.po_quantity, po.qty_delivered,
                   po.deliv_date, po.net_price, po.crcy
            FROM taex_reservasi t
            LEFT JOIN work_order wo ON wo."order" = t."order"
            LEFT JOIN sap_pr sp ON sp.pr = t.pr AND (sp.d IS NULL OR sp.d = '')
            LEFT JOIN sap_po po ON po.purchreq = t.pr AND (po.d IS NULL OR po.d = '')
            WHERE t.material IS NOT NULL AND t.material != '' {('AND ' + ' AND '.join(conds)) if conds else ''}
            LIMIT %s OFFSET %s
        """
        rows = query(sql, params + [limit, offset])
        return pd.DataFrame([dict(r) for r in rows])

    @st.cache_data(ttl=15)
    def count_tracking(search=""):
        conds, params = [], []
        if search:
            conds.append('(material ILIKE %s OR "order" ILIKE %s OR pr ILIKE %s)')
            p = f"%{search}%"; params.extend([p]*3)
        where = ("WHERE " + " AND ".join(conds) + " AND") if conds else "WHERE"
        sql = f"SELECT COUNT(*) AS c FROM taex_reservasi {where} material IS NOT NULL AND material != ''"
        r = query(sql, params)
        return int(r[0]["c"]) if r else 0

    def calc_status(row):
        pr, po = bool(row.get("pr")), bool(row.get("po_num"))
        qpo = float(row.get("po_quantity") or 0)
        qdel = float(row.get("qty_delivered") or 0)
        if not pr: return "no-pr"
        if not po: return "pr-created"
        if qdel <= 0: return "po-created"
        if qdel < qpo: return "partial"
        return "complete"

    status_map = {"🔴 Belum PR":"no-pr","🟡 PR Created":"pr-created",
                  "🔵 PO Created":"po-created","🟠 Partial Delivery":"partial","✅ Complete":"complete"}

    trk_total = count_tracking(search=trk_search)
    if trk_total == 0:
        st.markdown("""<div style="background:white;border-radius:10px;padding:48px;text-align:center;
            box-shadow:0 1px 3px rgba(0,0,0,0.07);">
            <div style="font-size:40px;opacity:0.4;margin-bottom:12px">🔍</div>
            <div style="font-size:15px;font-weight:700;color:#475569">Tidak ada data tracking</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:6px">Pastikan data TA-ex, Order, PR, dan PO sudah diupload</div>
        </div>""", unsafe_allow_html=True)
    else:
        ptrk, otrk = pagination("trk", trk_total, trk_ps)
        df_trk = build_tracking(search=trk_search, limit=trk_ps, offset=otrk)
        df_trk["status"] = df_trk.apply(calc_status, axis=1)

        if trk_status and not trk_status.startswith("—"):
            sc = status_map.get(trk_status)
            if sc: df_trk = df_trk[df_trk["status"] == sc]

        # ── Summary Cards ──
        cc = st.columns(8)
        total_ord = df_trk["order"].nunique() if "order" in df_trk.columns else 0
        has_pr  = (df_trk["pr"].notna() & (df_trk["pr"]!="")).sum() if "pr" in df_trk.columns else 0
        has_po  = (df_trk["po_num"].notna() & (df_trk["po_num"]!="")).sum() if "po_num" in df_trk.columns else 0
        partial = (df_trk["status"]=="partial").sum()
        complete= (df_trk["status"]=="complete").sum()
        no_pr   = (df_trk["status"]=="no-pr").sum()
        nilai   = df_trk["net_price"].fillna(0).sum() if "net_price" in df_trk.columns else 0

        card_data = [
            (total_ord,"Total Order","#1a56db"),
            (len(df_trk),"Total Material","#5b21b6"),
            (has_pr,"Sudah PR","#0e7490"),
            (has_po,"Sudah PO","#065f46"),
            (partial,"Partial","#c2410c"),
            (complete,"Complete","#059669"),
            (no_pr,"Belum PR","#b91c1c"),
            (f"Rp {nilai:,.0f}","Total Nilai PO","#374151"),
        ]
        for col, (v,l,c) in zip(cc, card_data):
            col.markdown(stat_card(v,l,c,c), unsafe_allow_html=True)

        st.markdown('<div class="table-card" style="margin-top:12px">', unsafe_allow_html=True)
        st.markdown(table_info_bar(len(df_trk), trk_total), unsafe_allow_html=True)
        cols_trk = [c for c in ["plant","equipment","order","reservno","revision","material","itm",
                                  "material_description","qty_reqmts","qty_stock","pr","pr_item","qty_pr",
                                  "del","fis","ict","pg","description","system_status","planner_group",
                                  "basic_start_date","basic_finish_date","req_date",
                                  "po_num","po_quantity","qty_delivered","deliv_date","net_price","crcy","status"]
                    if c in df_trk.columns]
        st.dataframe(df_trk[cols_trk], use_container_width=True, height=460, hide_index=True,
            column_config={
                "qty_reqmts":    st.column_config.NumberColumn("Qty Reqmts"),
                "qty_stock":     st.column_config.NumberColumn("Qty Stock"),
                "qty_pr":        st.column_config.NumberColumn("Qty PR"),
                "po_quantity":   st.column_config.NumberColumn("PO Qty"),
                "qty_delivered": st.column_config.NumberColumn("Qty Delivered"),
                "net_price":     st.column_config.NumberColumn("Net Price"),
            })
        st.markdown('</div>', unsafe_allow_html=True)

        trk_exp = st.download_button("📤 Export Tracking Excel",
                                     data=to_excel_bytes(df_trk,"Tracking"),
                                     file_name=f"Tracking_{datetime.now():%Y%m%d}.xlsx",
                                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                     key="trk_exp")
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 10 — AUDIT
# ══════════════════════════════════════════════════════════════
with tab_audit:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("🔎", "Audit — TA-ex vs PRISMA"), unsafe_allow_html=True)

    AUDIT_COLS = [
        ("equipment","Equipment"),("reservno","Reserv.No."),("revision","Revision"),
        ("material_description","Material Description"),("qty_reqmts","Reqmt Qty"),
        ("del","Del"),("fis","FIs"),("ict","ICt"),("pg","PG"),
        ("uom","BUn"),("recipient","Recipient"),("unloading_point","Unloading Point"),
        ("reqmts_date","Reqmt Date"),
    ]

    af1, af2, af3, af4 = st.columns([4, 2, 1, 0.7])
    with af1:
        aud_search = st.text_input("Cari", placeholder="🔍  Order, Material...",
                                   key="aud_search", label_visibility="collapsed")
    with af2:
        col_labels = ["— Semua Kolom —"] + [v for _,v in AUDIT_COLS]
        col_keys   = [""] + [k for k,_ in AUDIT_COLS]
        aud_col = st.selectbox("Kolom", col_labels, key="aud_col_sel", label_visibility="collapsed")
        aud_col_key = col_keys[col_labels.index(aud_col)]
    with af3:
        aud_ps = st.selectbox("Hal", [100,200,500], key="aud_ps", label_visibility="collapsed")
    with af4:
        if st.button("🔄", key="aud_refresh", use_container_width=True):
            st.cache_data.clear(); reset_page("aud"); st.rerun()

    try:
        changed_r = query("SELECT COUNT(DISTINCT (t.\"order\",t.material,t.itm)) AS c "
                          "FROM prisma_reservasi p "
                          "JOIN taex_reservasi t ON p.\"order\"=t.\"order\" AND p.material=t.material AND p.itm=t.itm "
                          "WHERE " + " OR ".join([f"p.{k} IS DISTINCT FROM t.{k}" for k,_ in AUDIT_COLS]))
        changed_count = int(changed_r[0]["c"]) if changed_r else 0
    except:
        changed_count = 0

    st.markdown(info_banner([
        ("Baris TA-ex", f"{counts['taex']:,}"),
        ("Baris PRISMA", f"{counts['prisma']:,}"),
        ("Baris Berubah", f"<b style='color:#b91c1c'>{changed_count:,}</b>"),
    ]), unsafe_allow_html=True)

    if changed_count == 0:
        st.markdown("""<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
            padding:20px;text-align:center;font-size:13px;color:#065f46;font-weight:600;">
            ✅ Tidak ada perbedaan — data TA-ex dan PRISMA konsisten!
        </div>""", unsafe_allow_html=True)
    else:
        @st.cache_data(ttl=10)
        def fetch_audit(search="", col_filter="", limit=100, offset=0):
            target = [(col_filter, next(v for k,v in AUDIT_COLS if k==col_filter))] if col_filter else AUDIT_COLS
            unions = []
            for key, label in target:
                pv = f"COALESCE(p.{key}::text,'')"
                tv = f"COALESCE(t.{key}::text,'')"
                u = (f"SELECT t.\"order\" AS order_val,t.material,t.itm,"
                     f"'{key}' AS col_key,'{label}' AS col_label,"
                     f"{pv} AS val_prisma,{tv} AS val_taex "
                     f"FROM prisma_reservasi p "
                     f"JOIN taex_reservasi t ON p.\"order\"=t.\"order\" AND p.material=t.material AND p.itm=t.itm "
                     f"WHERE p.{key} IS DISTINCT FROM t.{key}")
                if search:
                    u += f" AND (t.\"order\" ILIKE '%{search}%' OR t.material ILIKE '%{search}%')"
                unions.append(u)
            if not unions: return pd.DataFrame()
            sql = " UNION ALL ".join(unions) + f" ORDER BY order_val,material,itm,col_key LIMIT {limit} OFFSET {offset}"
            rows = query(sql)
            return pd.DataFrame([dict(r) for r in rows])

        paud, oaud = pagination("aud", changed_count * len(AUDIT_COLS), aud_ps)
        df_audit = fetch_audit(search=aud_search, col_filter=aud_col_key, limit=aud_ps, offset=oaud)
        if not df_audit.empty:
            st.markdown('<div class="table-card">', unsafe_allow_html=True)
            st.markdown(table_info_bar(len(df_audit), changed_count, "perbedaan ditemukan"), unsafe_allow_html=True)
            st.dataframe(
                df_audit.rename(columns={"order_val":"Order","col_label":"Kolom",
                                         "val_prisma":"Nilai PRISMA","val_taex":"Nilai TA-ex"}),
                use_container_width=True, height=440, hide_index=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("📤 Export Audit Excel",
                               data=to_excel_bytes(df_audit,"Audit"),
                               file_name=f"Audit_{datetime.now():%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="aud_exp")
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TAB 11 — RESET
# ══════════════════════════════════════════════════════════════
with tab_reset:
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown(section_title("⚙", "Reset Data"), unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#fff1f2;border:1.5px solid #fecdd3;border-radius:8px;padding:16px 20px;
                margin-bottom:16px;border-left:4px solid #e11d48;">
        <b style="color:#9f1239;font-size:13px">⚠️ PERINGATAN</b><br>
        <span style="font-size:12px;color:#be123c;line-height:1.7">
        Tindakan ini akan menghapus <b>SEMUA data</b> dari seluruh tabel.<br>
        Tindakan ini <b>tidak bisa dibatalkan</b>.
        </span>
    </div>
    """, unsafe_allow_html=True)

    rc1, rc2 = st.columns([2, 4])
    with rc1:
        confirm_text = st.text_input("Ketik RESET untuk konfirmasi",
                                     placeholder="RESET",
                                     key="reset_confirm")
        if st.button("🗑 Reset Semua Data", type="primary", use_container_width=True):
            if confirm_text.strip().upper() == "RESET":
                with st.spinner("⏳ Mereset semua data..."):
                    try:
                        for tbl in ["taex_reservasi","prisma_reservasi","kumpulan_summary",
                                    "sap_pr","sap_po","work_order","app_state"]:
                            execute(f"DELETE FROM {tbl}")
                        for seq in ["taex_reservasi_id_seq","prisma_reservasi_id_seq",
                                    "kumpulan_summary_id_seq","sap_pr_id_seq",
                                    "sap_po_id_seq","work_order_id_seq"]:
                            try: execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                            except: pass
                        st.session_state.kk_data = []
                        st.session_state.kk_code = None
                        st.session_state.summary_data = []
                        st.cache_data.clear()
                        st.success("✅ Semua data berhasil direset!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal reset: {e}")
            else:
                st.warning("Ketik RESET (huruf kapital) untuk konfirmasi.")
    st.markdown('</div>', unsafe_allow_html=True)