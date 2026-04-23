"""
app.py — PRISMA · TA-ex System (Streamlit Version)
Versi Python Streamlit dari sistem manajemen reservasi material SAP.

Jalankan: streamlit run app.py
"""
import io
import random
import string
import traceback
from datetime import datetime

import pandas as pd
import streamlit as st

# ─── Page config (HARUS pertama) ───────────────────────────────
st.set_page_config(
    page_title="PRISMA · TA-ex System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Local imports ──────────────────────────────────────────────
from styles import inject_css, card, badge, status_label, info_bar
from database import migrate, query, execute, get_state, set_state
from bulk_ops import (
    bulk_replace_taex, bulk_replace_prisma, bulk_replace_pr,
    bulk_replace_po, bulk_replace_kumpulan, bulk_replace_order,
)

# ─── CSS ────────────────────────────────────────────────────────
inject_css()

# ─── DB INIT (hanya sekali per session) ─────────────────────────
if "db_migrated" not in st.session_state:
    try:
        migrate()
        st.session_state.db_migrated = True
    except Exception as e:
        st.error(f"❌ Gagal konek ke database: {e}")
        st.stop()

# ─── SESSION STATE INIT ──────────────────────────────────────────
def _init_state():
    defaults = {
        "kk_data": [],
        "kk_code": None,
        "summary_data": [],
        "current_tab": "TA-ex Reservasi",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════
def fmt_date(val):
    if not val:
        return ""
    s = str(val).strip()
    import re
    m = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', s)
    if m: return f"{m.group(1).zfill(2)}-{m.group(2).zfill(2)}-{m.group(3)}"
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s


def generate_kk_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10))


def n(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try: return float(v)
    except: return None


def to_excel_bytes(df: pd.DataFrame, sheet_name="Sheet1") -> bytes:
    df = df.copy()
    # Hapus kolom timestamp DB (created_at, updated_at) — tidak perlu di export
    drop_cols = [c for c in df.columns if c in ("created_at", "updated_at")]
    if drop_cols:
        df = df.drop(columns=drop_cols)
    # Strip timezone dari kolom datetime agar Excel tidak error
    for col in df.columns:
        if hasattr(df[col], "dt") and df[col].dtype.tz is not None:
            df[col] = df[col].dt.tz_localize(None)
    # Konversi kolom object ke string bersih (hindari mixed types)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna("").astype(str)
            df[col] = df[col].replace("nan", "").replace("None", "")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()


def load_excel(uploaded_file) -> pd.DataFrame:
    """Baca Excel / CSV ke DataFrame dengan pandas — cepat untuk ratusan ribu baris."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
    else:
        return pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)


# ─── COUNT HELPERS ──────────────────────────────────────────────
@st.cache_data(ttl=5)
def count_table(table):
    q = "SELECT COUNT(*) AS c FROM " + table
    row = query(q)
    return int(row[0]["c"]) if row else 0


def get_counts():
    return {
        "taex":     count_table("taex_reservasi"),
        "prisma":   count_table("prisma_reservasi"),
        "kumpulan": count_table("kumpulan_summary"),
        "pr":       count_table("sap_pr"),
        "po":       count_table("sap_po"),
        "order":    count_table("work_order"),
    }


# ─── FETCH HELPERS ──────────────────────────────────────────────
@st.cache_data(ttl=10)
def fetch_taex(search="", pr_filter="", limit=5000, offset=0, order_by="id", order_dir="ASC"):
    conds, params = [], []
    if search:
        conds.append("""(material ILIKE %s OR material_description ILIKE %s
                         OR "order" ILIKE %s OR equipment ILIKE %s
                         OR pr ILIKE %s OR reservno ILIKE %s)""")
        p = f"%{search}%"
        params.extend([p, p, p, p, p, p])
    if pr_filter:
        conds.append("pr = %s"); params.append(pr_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    safe_ob = order_by if order_by in {
        "id","equipment",'"order"',"revision","material","itm",
        "qty_reqmts","qty_stock","pr","qty_pr","reservno","res_price"
    } else "id"
    safe_dir = "DESC" if order_dir.upper() == "DESC" else "ASC"
    sql = f"""SELECT * FROM taex_reservasi {where}
              ORDER BY {safe_ob} {safe_dir}
              LIMIT %s OFFSET %s"""
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=10)
def fetch_prisma(search="", order_filter="", limit=5000, offset=0):
    conds, params = [], []
    if search:
        conds.append("""(material ILIKE %s OR material_description ILIKE %s
                         OR "order" ILIKE %s OR equipment ILIKE %s)""")
        p = f"%{search}%"; params.extend([p, p, p, p])
    if order_filter:
        conds.append('"order" = %s'); params.append(order_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sql = f'SELECT * FROM prisma_reservasi {where} ORDER BY id LIMIT %s OFFSET %s'
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=10)
def fetch_sap_pr(search="", limit=5000, offset=0):
    conds, params = [], []
    if search:
        conds.append("(pr ILIKE %s OR material ILIKE %s OR material_description ILIKE %s)")
        p = f"%{search}%"; params.extend([p, p, p])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sql = f"SELECT * FROM sap_pr {where} ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=10)
def fetch_sap_po(search="", limit=5000, offset=0):
    conds, params = [], []
    if search:
        conds.append("(po ILIKE %s OR purchreq ILIKE %s OR material ILIKE %s)")
        p = f"%{search}%"; params.extend([p, p, p])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sql = f"SELECT * FROM sap_po {where} ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=10)
def fetch_kumpulan(search="", code_filter="", limit=5000, offset=0):
    conds, params = [], []
    if search:
        conds.append("(material ILIKE %s OR code_tracking ILIKE %s)")
        p = f"%{search}%"; params.extend([p, p])
    if code_filter:
        conds.append("code_tracking = %s"); params.append(code_filter)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sql = f"SELECT * FROM kumpulan_summary {where} ORDER BY id LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


@st.cache_data(ttl=10)
def fetch_order(search="", limit=5000, offset=0):
    conds, params = [], []
    if search:
        conds.append("""("order" ILIKE %s OR description ILIKE %s OR equipment ILIKE %s)""")
        p = f"%{search}%"; params.extend([p, p, p])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    sql = f'SELECT * FROM work_order {where} ORDER BY id LIMIT %s OFFSET %s'
    params.extend([limit, offset])
    rows = query(sql, params)
    return pd.DataFrame([dict(r) for r in rows])


# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════
st.markdown("""
<div class="app-header">
    <h1>📦 PRISMA · TA-ex System</h1>
    <div class="subtitle">Material Reservation &amp; PR Management</div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# TABS UTAMA
# ════════════════════════════════════════════════════════════════
counts = get_counts()
tabs = st.tabs([
    f"📦 TA-ex Reservasi ({counts['taex']:,})",
    f"📋 PRISMA Reservasi ({counts['prisma']:,})",
    f"📝 Kertas Kerja ({len(st.session_state.kk_data)})",
    f"📊 Summary ({len(st.session_state.summary_data)})",
    f"🗂 Kumpulan Summary ({counts['kumpulan']:,})",
    f"🧾 SAP PR ({counts['pr']:,})",
    f"📋 Order ({counts['order']:,})",
    f"🛒 PO ({counts['po']:,})",
    "🔍 Tracking",
    "🔎 Audit",
    "⚙ Reset",
])

(
    tab_taex, tab_prisma, tab_kk, tab_summary, tab_kumpulan,
    tab_pr, tab_order, tab_po, tab_tracking, tab_audit, tab_reset
) = tabs


# ════════════════════════════════════════════════════════════════
# TAB 1 — TA-EX RESERVASI
# ════════════════════════════════════════════════════════════════
with tab_taex:
    st.subheader("📦 TA-ex Reservasi")

    # ── Filter Bar ──
    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    with col1:
        taex_search = st.text_input("🔍 Cari", placeholder="Material, deskripsi, order...", key="taex_search")
    with col2:
        # Distinct PR values
        pr_vals = query('SELECT DISTINCT pr FROM taex_reservasi WHERE pr IS NOT NULL ORDER BY pr LIMIT 500')
        pr_options = [""] + [r["pr"] for r in pr_vals]
        taex_pr_filter = st.selectbox("PR", pr_options, key="taex_pr_filter")
    with col3:
        taex_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="taex_limit")
    with col4:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh", key="taex_refresh"):
            st.cache_data.clear()

    # ── Upload & Download ──
    col_ul, col_tpl, col_exp = st.columns([1, 1, 1])
    with col_ul:
        taex_file = st.file_uploader("📥 Upload Excel TA-ex", type=["xlsx", "xls", "csv"], key="taex_upload")
        if taex_file:
            upload_mode = st.radio(
                "Mode Upload",
                ["Tambahkan (UPSERT)", "Ganti Semua (Replace)"],
                key="taex_upload_mode",
                horizontal=True,
            )
            if st.button("✅ Import TA-ex", key="taex_import_btn"):
                with st.spinner(f"⏳ Membaca {taex_file.name}..."):
                    try:
                        df_up = load_excel(taex_file)
                        mode = "append" if "Tambahkan" in upload_mode else "replace"
                        with st.spinner(f"💾 Menyimpan {len(df_up):,} baris ke database..."):
                            cnt = bulk_replace_taex(df_up, mode=mode)
                        st.success(f"✅ {cnt:,} baris berhasil diimport!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal import: {e}")
                        st.text(traceback.format_exc())

    with col_tpl:
        tpl_cols = [
            "PlPl","Equipment","Order","Reserv.No.","Revision","Material","Itm",
            "Material Description","Reqmt Qty","Qty_Stock","PR","Item","Qty_PR",
            "Cost Ctrs","SLoc","Del","FIs","ICt","PG","Recipient","Unloading Point",
            "Reqmt Date","Qty. f. avail.check","Qty Withdrawn","BUn","G/L Acct",
            "Price","per","Crcy"
        ]
        tpl_df = pd.DataFrame(columns=tpl_cols)
        st.download_button(
            "📋 Download Template",
            data=to_excel_bytes(tpl_df, "Template TA-ex"),
            file_name="Template_TAex_Reservasi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="taex_tpl_btn"
        )

    with col_exp:
        if counts["taex"] > 0:
            df_exp = fetch_taex(search=taex_search, pr_filter=taex_pr_filter, limit=50000)
            if not df_exp.empty:
                col_map = {
                    "id":"ID","plant":"PlPl","equipment":"Equipment","order":"Order",
                    "reservno":"Reserv.No.","revision":"Revision","material":"Material",
                    "itm":"Itm","material_description":"Material Description",
                    "qty_reqmts":"Reqmt Qty","qty_stock":"Qty_Stock","pr":"PR","item":"Item",
                    "qty_pr":"Qty_PR","cost_ctrs":"Cost Ctrs","sloc":"SLoc",
                    "del":"Del","fis":"FIs","ict":"ICt","pg":"PG",
                    "recipient":"Recipient","unloading_point":"Unloading Point",
                    "reqmts_date":"Reqmt Date","qty_f_avail_check":"Qty. f. avail.check",
                    "qty_withdrawn":"Qty Withdrawn","uom":"BUn","gl_acct":"G/L Acct",
                    "res_price":"Price","res_per":"per","res_curr":"Crcy",
                }
                df_exp_renamed = df_exp.rename(columns=col_map)
                st.download_button(
                    "📤 Export Excel",
                    data=to_excel_bytes(df_exp_renamed, "TA-ex Reservasi"),
                    file_name=f"TAex_Reservasi_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="taex_exp_btn"
                )

    # ── Tabel ──
    df_taex = fetch_taex(search=taex_search, pr_filter=taex_pr_filter, limit=taex_limit)
    if df_taex.empty:
        st.info("📭 Belum ada data. Upload file Excel untuk memulai.")
    else:
        st.caption(f"Menampilkan {len(df_taex):,} dari {counts['taex']:,} baris")

        col_display = [
            "id","plant","equipment","order","reservno","revision",
            "material","itm","material_description","qty_reqmts","qty_stock",
            "pr","item","qty_pr","cost_ctrs","sloc","del","fis","ict","pg",
            "recipient","unloading_point","reqmts_date",
            "qty_f_avail_check","qty_withdrawn","uom","gl_acct",
            "res_price","res_per","res_curr"
        ]
        available = [c for c in col_display if c in df_taex.columns]
        st.dataframe(
            df_taex[available],
            use_container_width=True,
            height=500,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "plant": "PlPl",
                "equipment": st.column_config.TextColumn("Equipment", width="medium"),
                "order": st.column_config.TextColumn("Order", width="medium"),
                "reservno": "Reserv.No.",
                "material": st.column_config.TextColumn("Material", width="medium"),
                "material_description": st.column_config.TextColumn("Material Description", width="large"),
                "qty_reqmts": st.column_config.NumberColumn("Reqmt Qty"),
                "qty_stock": st.column_config.NumberColumn("Qty_Stock"),
                "pr": "PR",
                "qty_pr": st.column_config.NumberColumn("Qty_PR"),
                "res_price": st.column_config.NumberColumn("Price"),
            },
            hide_index=True,
        )


# ════════════════════════════════════════════════════════════════
# TAB 2 — PRISMA RESERVASI
# ════════════════════════════════════════════════════════════════
with tab_prisma:
    st.subheader("📋 PRISMA Reservasi")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        pr_search = st.text_input("🔍 Cari", placeholder="Material, deskripsi...", key="pr_search")
    with col2:
        ord_vals = query('SELECT DISTINCT "order" FROM prisma_reservasi WHERE "order" IS NOT NULL ORDER BY "order" LIMIT 1000')
        ord_options = [""] + [r["order"] for r in ord_vals]
        pr_ord_filter = st.selectbox("Order", ord_options, key="pr_ord_filter")
    with col3:
        pr_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="pr_limit")

    # ── Action Buttons ──
    col_sync, col_kk, col_exp = st.columns([1, 1, 1])

    with col_sync:
        if st.button("🔄 Sinkron dari TA-ex", key="sync_taex_btn"):
            with st.spinner("⏳ Mengambil data TA-ex..."):
                try:
                    all_taex = query("""
                        SELECT * FROM taex_reservasi
                        WHERE UPPER(ict) = 'L'
                          AND (del IS NULL OR UPPER(del) != 'X')
                          AND (fis IS NULL OR UPPER(fis) != 'X')
                    """)
                    existing = query('SELECT "order", material, itm FROM prisma_reservasi')
                    exist_set = {(r["order"], r["material"], r["itm"]) for r in existing}

                    new_rows, skip_count = [], 0
                    for t in all_taex:
                        key = (t["order"], t["material"], t["itm"])
                        if key in exist_set:
                            skip_count += 1
                            continue
                        new_rows.append(t)

                    if new_rows:
                        from psycopg2.extras import execute_values
                        from database import get_conn, release_conn
                        conn = get_conn()
                        try:
                            with conn.cursor() as cur:
                                sql = """
                                    INSERT INTO prisma_reservasi
                                    (plant, equipment, revision, "order", reservno, itm, material,
                                     material_description, del, fis, ict, pg, recipient, unloading_point,
                                     reqmts_date, qty_reqmts, uom)
                                    VALUES %s
                                """
                                vals = [(
                                    t["plant"], t["equipment"], t["revision"], t["order"],
                                    t["reservno"], t["itm"], t["material"],
                                    t["material_description"], t["del"], t["fis"], t["ict"],
                                    t["pg"], t["recipient"], t["unloading_point"],
                                    t["reqmts_date"], t["qty_reqmts"], t["uom"]
                                ) for t in new_rows]
                                execute_values(cur, sql, vals)
                            conn.commit()
                        finally:
                            release_conn(conn)

                    st.success(f"✅ {len(new_rows)} baris baru ditambahkan, {skip_count} sudah ada.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal sinkron: {e}")

    with col_kk:
        if st.button("📝 Buat Kertas Kerja", key="open_kk_modal"):
            st.session_state["show_kk_form"] = True

    with col_exp:
        df_pr_all = fetch_prisma(search=pr_search, order_filter=pr_ord_filter, limit=50000)
        if not df_pr_all.empty:
            st.download_button(
                "📤 Export Excel",
                data=to_excel_bytes(df_pr_all, "PRISMA Reservasi"),
                file_name=f"PRISMA_Reservasi_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="pr_exp_btn"
            )

    # ── Form Kertas Kerja ──
    if st.session_state.get("show_kk_form"):
        with st.expander("📝 Buat Kertas Kerja", expanded=True):
            kk_code_new = generate_kk_code()
            st.text_input("Kode KK (otomatis)", value=kk_code_new, disabled=True, key="kk_code_display")

            pg_type = st.selectbox(
                "Planner Group",
                ["", "TA (PG akhiran T)", "OH (PG akhiran O)", "Rutin (PG akhiran R)", "All (Semua PG)"],
                key="kk_pg_type"
            )

            if pg_type:
                # Filter WO berdasarkan PG
                used_orders = {r["order"] for r in query(
                    'SELECT DISTINCT "order" FROM prisma_reservasi WHERE code_kertas_kerja IS NOT NULL'
                )}
                prisma_rows = query('SELECT DISTINCT "order", pg FROM prisma_reservasi WHERE code_kertas_kerja IS NULL')

                def pg_match(pg_val, pg_type):
                    if not pg_val: return False
                    pg_val = str(pg_val).strip().upper()
                    if "TA" in pg_type: return pg_val.endswith("T")
                    if "OH" in pg_type: return pg_val.endswith("O")
                    if "Rutin" in pg_type: return pg_val.endswith("R")
                    return True

                available_orders = sorted({
                    r["order"] for r in prisma_rows
                    if r["order"] not in used_orders and pg_match(r["pg"], pg_type)
                })

                if available_orders:
                    # Pilih Semua / Hapus Semua pakai flag terpisah, bukan set widget key langsung
                    col_all, col_none = st.columns(2)
                    if col_all.button("Pilih Semua", key="kk_select_all"):
                        st.session_state["kk_wo_default"] = available_orders
                        st.rerun()
                    if col_none.button("Hapus Semua", key="kk_deselect"):
                        st.session_state["kk_wo_default"] = []
                        st.rerun()

                    default_val = st.session_state.get("kk_wo_default", [])
                    selected_orders = st.multiselect(
                        f"Work Order ({len(available_orders)} tersedia)",
                        available_orders,
                        default=default_val,
                        key="kk_wo_select"
                    )

                    if st.button("✅ Buat Kertas Kerja", key="create_kk_btn"):
                        if not selected_orders:
                            st.warning("Pilih minimal satu Work Order!")
                        else:
                            sel_set = set(selected_orders)
                            source = query("""
                                SELECT * FROM prisma_reservasi
                                WHERE "order" = ANY(%s)
                                  AND (del IS NULL OR UPPER(del) != 'X')
                                  AND (fis IS NULL OR UPPER(fis) != 'X')
                            """, (list(sel_set),))
                            if not source:
                                st.warning("Tidak ada data yang memenuhi syarat.")
                            else:
                                kk_rows = [dict(r) for r in source]
                                for row in kk_rows:
                                    row["CodeKertasKerja"] = kk_code_new
                                st.session_state.kk_data = kk_rows
                                st.session_state.kk_code = kk_code_new
                                set_state("kk_current", {"code": kk_code_new, "data": kk_rows})
                                st.success(f"✅ Kertas Kerja {kk_code_new} berhasil dibuat dengan {len(kk_rows)} baris!")
                                st.session_state["show_kk_form"] = False
                                st.rerun()
                else:
                    st.info("Tidak ada WO tersedia untuk Planner Group ini.")

            if st.button("✕ Batal", key="cancel_kk"):
                st.session_state["show_kk_form"] = False
                st.rerun()

    # ── Tabel ──
    df_pr = fetch_prisma(search=pr_search, order_filter=pr_ord_filter, limit=pr_limit)
    if df_pr.empty:
        st.info("📭 Belum ada data. Klik 'Sinkron dari TA-ex' untuk memulai.")
    else:
        st.caption(f"Menampilkan {len(df_pr):,} dari {counts['prisma']:,} baris")
        col_show = [c for c in [
            "id","plant","equipment","revision","order","reservno","itm",
            "material","material_description","del","fis","ict","pg",
            "recipient","unloading_point","reqmts_date","qty_reqmts","uom",
            "pr_prisma","item_prisma","qty_pr_prisma","qty_stock_onhand","code_kertas_kerja"
        ] if c in df_pr.columns]
        st.dataframe(df_pr[col_show], use_container_width=True, height=500, hide_index=True)


# ════════════════════════════════════════════════════════════════
# TAB 3 — KERTAS KERJA
# ════════════════════════════════════════════════════════════════
with tab_kk:
    st.subheader("📝 Kertas Kerja")

    # Load dari DB jika session kosong
    if not st.session_state.kk_data:
        saved_kk = get_state("kk_current")
        if saved_kk and isinstance(saved_kk, dict):
            st.session_state.kk_data = saved_kk.get("data", [])
            st.session_state.kk_code = saved_kk.get("code")

    kk_data = st.session_state.kk_data
    kk_code = st.session_state.kk_code

    if kk_data:
        st.markdown(info_bar([
            ("Kode KK", kk_code or "—"),
            ("Total Baris", len(kk_data)),
            ("Material Unik", len({r.get("material") for r in kk_data}))
        ]), unsafe_allow_html=True)

        kk_search = st.text_input("🔍 Cari", placeholder="Material, deskripsi...", key="kk_search")

        df_kk = pd.DataFrame(kk_data)
        if kk_search:
            mask = df_kk.apply(
                lambda row: any(kk_search.lower() in str(v).lower() for v in row), axis=1
            )
            df_kk = df_kk[mask]

        col_show = [c for c in [
            "plant","equipment","revision","order","reservno","itm",
            "material","material_description","qty_reqmts","qty_stock_onhand","code_kertas_kerja"
        ] if c in df_kk.columns]

        # Kolom qty_stock_onhand bisa diedit
        edited_df = st.data_editor(
            df_kk[col_show] if col_show else df_kk,
            use_container_width=True,
            height=400,
            hide_index=True,
            column_config={
                "qty_stock_onhand": st.column_config.NumberColumn("Qty Stock Onhand", help="Isi stock fisik"),
            },
            disabled=[c for c in col_show if c != "qty_stock_onhand"],
            key="kk_editor"
        )

        # Sync edits back
        if "qty_stock_onhand" in edited_df.columns:
            for i, row in edited_df.iterrows():
                if i < len(st.session_state.kk_data):
                    st.session_state.kk_data[i]["qty_stock_onhand"] = row.get("qty_stock_onhand")

        col_sub, col_cancel = st.columns([1, 4])
        with col_sub:
            if st.button("✅ Submit Kertas Kerja", key="submit_kk"):
                # Buat Summary
                summary_map = {}
                for r in st.session_state.kk_data:
                    mat = r.get("material")
                    if not mat: continue
                    if mat not in summary_map:
                        summary_map[mat] = {
                            "Plant": r.get("plant"), "Material": mat,
                            "Material_Description": r.get("material_description"),
                            "Qty_Req": 0, "Qty_Stock": 0, "CodeTracking": kk_code,
                            "Order": r.get("order"), "Equipment": r.get("equipment"),
                            "Revision": r.get("revision"), "Reservno": r.get("reservno"),
                            "Itm": r.get("itm"),
                        }
                    summary_map[mat]["Qty_Req"] += float(r.get("qty_reqmts") or 0)
                    summary_map[mat]["Qty_Stock"] += float(r.get("qty_stock_onhand") or 0)

                summary_rows = []
                for r in summary_map.values():
                    r["Qty_To_PR"] = max(0, r["Qty_Req"] - r["Qty_Stock"])
                    summary_rows.append(r)

                st.session_state.summary_data = summary_rows

                # Update PRISMA dengan CodeKertasKerja
                with st.spinner("💾 Menyimpan..."):
                    from psycopg2.extras import execute_values
                    from database import get_conn, release_conn
                    conn = get_conn()
                    try:
                        with conn.cursor() as cur:
                            for r in st.session_state.kk_data:
                                cur.execute("""
                                    UPDATE prisma_reservasi
                                    SET code_kertas_kerja=%s, qty_stock_onhand=%s, updated_at=NOW()
                                    WHERE "order"=%s AND material=%s AND itm=%s
                                """, (
                                    kk_code,
                                    r.get("qty_stock_onhand"),
                                    r.get("order"), r.get("material"), r.get("itm")
                                ))
                        conn.commit()
                    finally:
                        release_conn(conn)

                    set_state("summary_current", summary_rows)
                    set_state("kk_current", {"code": None, "data": []})
                    st.session_state.kk_data = []

                st.success(f"✅ Kertas Kerja disubmit! {len(summary_rows)} material dalam Summary.")
                st.cache_data.clear()
                st.rerun()
    else:
        st.info("📭 Belum ada Kertas Kerja. Buat dari tab 'PRISMA Reservasi' → tombol 'Buat Kertas Kerja'.")


# ════════════════════════════════════════════════════════════════
# TAB 4 — SUMMARY
# ════════════════════════════════════════════════════════════════
with tab_summary:
    st.subheader("📊 Summary")

    # Load dari DB jika session kosong
    if not st.session_state.summary_data:
        saved_sum = get_state("summary_current")
        if saved_sum:
            st.session_state.summary_data = saved_sum

    sum_data = st.session_state.summary_data
    kk_code_sum = st.session_state.kk_code

    if sum_data:
        total_qty_req = sum(float(r.get("Qty_Req") or 0) for r in sum_data)
        total_qty_stock = sum(float(r.get("Qty_Stock") or 0) for r in sum_data)
        st.markdown(info_bar([
            ("Kode KK", kk_code_sum or "—"),
            ("Material Unik", len(sum_data)),
            ("Total Qty_Req", f"{total_qty_req:,.0f}"),
            ("Total Qty_Stock", f"{total_qty_stock:,.0f}"),
        ]), unsafe_allow_html=True)

        sum_search = st.text_input("🔍 Cari", placeholder="Material, deskripsi...", key="sum_search")
        df_sum = pd.DataFrame(sum_data)
        if sum_search:
            mask = df_sum.apply(
                lambda row: any(sum_search.lower() in str(v).lower() for v in row), axis=1
            )
            df_sum = df_sum[mask]

        col_show = [c for c in [
            "Plant","Material","Material_Description","Qty_Req","Qty_Stock","Qty_To_PR","CodeTracking"
        ] if c in df_sum.columns]

        st.dataframe(
            df_sum[col_show] if col_show else df_sum,
            use_container_width=True, height=400, hide_index=True,
            column_config={
                "Qty_Req":    st.column_config.NumberColumn("Qty Req"),
                "Qty_Stock":  st.column_config.NumberColumn("Qty Stock"),
                "Qty_To_PR":  st.column_config.NumberColumn("Qty to PR"),
            }
        )

        col_sub2, col_exp_sum = st.columns([1, 1])
        with col_sub2:
            if st.button("✅ Submit & Simpan ke Kumpulan Summary", key="submit_summary"):
                with st.spinner("💾 Menyimpan ke Kumpulan Summary..."):
                    # Hapus entry dengan code yang sama, tambah baru
                    curr_code = st.session_state.kk_code or sum_data[0].get("CodeTracking") if sum_data else None
                    if curr_code:
                        execute("DELETE FROM kumpulan_summary WHERE code_tracking = %s", (curr_code,))
                    df_new = pd.DataFrame(sum_data)
                    bulk_replace_kumpulan(df_new)
                    set_state("summary_current", [])
                    st.session_state.summary_data = []
                    st.session_state.kk_code = None
                st.success("✅ Summary tersimpan di Kumpulan Summary!")
                st.cache_data.clear()
                st.rerun()

        with col_exp_sum:
            st.download_button(
                "📤 Export Excel",
                data=to_excel_bytes(pd.DataFrame(sum_data), "Summary"),
                file_name=f"Summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="sum_exp"
            )
    else:
        st.info("📭 Belum ada data Summary. Submit Kertas Kerja terlebih dahulu.")


# ════════════════════════════════════════════════════════════════
# TAB 5 — KUMPULAN SUMMARY
# ════════════════════════════════════════════════════════════════
with tab_kumpulan:
    st.subheader("🗂 Kumpulan Summary")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        ks_search = st.text_input("🔍 Cari", placeholder="Material, code tracking...", key="ks_search")
    with col2:
        code_vals = query("SELECT DISTINCT code_tracking FROM kumpulan_summary WHERE code_tracking IS NOT NULL ORDER BY code_tracking")
        code_options = [""] + [r["code_tracking"] for r in code_vals]
        ks_code_filter = st.selectbox("Code Tracking", code_options, key="ks_code_filter")
    with col3:
        ks_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="ks_limit")

    col_pr_sync, col_exp_ks = st.columns([1, 2])
    with col_pr_sync:
        if st.button("🔄 Sinkron PR", key="pr_sync_btn"):
            st.session_state["show_pr_sync"] = True

    with col_exp_ks:
        df_ks_exp = fetch_kumpulan(limit=50000)
        if not df_ks_exp.empty:
            st.download_button(
                "📤 Export Excel",
                data=to_excel_bytes(df_ks_exp, "Kumpulan Summary"),
                file_name=f"Kumpulan_Summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="ks_exp"
            )

    # ── Sinkron PR ──
    if st.session_state.get("show_pr_sync"):
        with st.expander("🔄 Sinkronisasi PR dari SAP PR", expanded=True):
            kumpulan_rows = query("SELECT * FROM kumpulan_summary")
            pr_rows = query("SELECT * FROM sap_pr")

            matched, unmatched = [], []
            for k in kumpulan_rows:
                pr_item = next((
                    p for p in pr_rows
                    if p["material"] == k["material"]
                    and (p["tracking_no"] == k["code_tracking"] or p["tracking"] == k["code_tracking"])
                ), None)
                if pr_item:
                    matched.append({"Material": k["material"], "Desc": k["material_description"],
                                    "PR": pr_item["pr"], "Qty_PR": pr_item["qty_pr"],
                                    "Tracking": k["code_tracking"]})
                else:
                    unmatched.append(k["material"])

            if matched:
                st.success(f"✅ {len(matched)} material akan disinkron")
                st.dataframe(pd.DataFrame(matched), use_container_width=True, hide_index=True)
            if unmatched:
                st.warning(f"⚠️ {len(unmatched)} material tidak ditemukan di SAP PR")

            col_run, col_cancel = st.columns([1, 4])
            with col_run:
                if st.button("▶ Jalankan Sinkron", key="run_pr_sync"):
                    with st.spinner("⏳ Menyinkron..."):
                        from database import get_conn, release_conn
                        conn = get_conn()
                        try:
                            with conn.cursor() as cur:
                                for k in kumpulan_rows:
                                    pr_item = next((
                                        p for p in pr_rows
                                        if p["material"] == k["material"]
                                        and (p["tracking_no"] == k["code_tracking"]
                                             or p["tracking"] == k["code_tracking"])
                                    ), None)
                                    if pr_item:
                                        qty_to_pr = max(0,
                                            float(k["qty_req"] or 0)
                                            - float(k["qty_stock"] or 0)
                                            - float(pr_item["qty_pr"] or 0)
                                        )
                                        cur.execute("""
                                            UPDATE kumpulan_summary
                                            SET qty_pr=%s, qty_to_pr=%s, updated_at=NOW()
                                            WHERE id=%s
                                        """, (pr_item["qty_pr"], qty_to_pr, k["id"]))
                                        cur.execute("""
                                            UPDATE prisma_reservasi
                                            SET pr_prisma=%s, qty_pr_prisma=%s, updated_at=NOW()
                                            WHERE material=%s AND code_kertas_kerja=%s
                                        """, (pr_item["pr"], pr_item["qty_pr"],
                                              k["material"], k["code_tracking"]))
                            conn.commit()
                        finally:
                            release_conn(conn)

                    st.success(f"✅ Sinkron selesai! {len(matched)} material diupdate.")
                    st.session_state["show_pr_sync"] = False
                    st.cache_data.clear()
                    st.rerun()
            with col_cancel:
                if st.button("✕ Batal", key="cancel_pr_sync"):
                    st.session_state["show_pr_sync"] = False
                    st.rerun()

    df_ks = fetch_kumpulan(search=ks_search, code_filter=ks_code_filter, limit=ks_limit)
    if df_ks.empty:
        st.info("📭 Belum ada data. Submit Summary terlebih dahulu.")
    else:
        st.caption(f"Menampilkan {len(df_ks):,} dari {counts['kumpulan']:,} baris")
        col_show = [c for c in [
            "plant","material","material_description","qty_req","qty_stock",
            "qty_pr","qty_to_pr","code_tracking"
        ] if c in df_ks.columns]
        st.dataframe(df_ks[col_show], use_container_width=True, height=400, hide_index=True,
                     column_config={
                         "qty_req": st.column_config.NumberColumn("Qty Req"),
                         "qty_stock": st.column_config.NumberColumn("Qty Stock"),
                         "qty_pr": st.column_config.NumberColumn("Qty PR"),
                         "qty_to_pr": st.column_config.NumberColumn("Qty to PR"),
                     })


# ════════════════════════════════════════════════════════════════
# TAB 6 — SAP PR
# ════════════════════════════════════════════════════════════════
with tab_pr:
    st.subheader("🧾 SAP PR")

    col1, col2 = st.columns([3, 1])
    with col1:
        sap_search = st.text_input("🔍 Cari", placeholder="Material, PR, tracking...", key="sap_search")
    with col2:
        sap_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="sap_limit")

    col_ul_sap, col_tpl_sap, col_exp_sap = st.columns([1, 1, 1])
    with col_ul_sap:
        sap_file = st.file_uploader("📥 Upload Excel SAP PR", type=["xlsx","xls","csv"], key="sap_upload")
        if sap_file:
            sap_mode = st.radio("Mode", ["Ganti Semua (Replace)", "Tambahkan (Append)"],
                                horizontal=True, key="sap_mode")
            if st.button("✅ Import SAP PR", key="sap_import"):
                with st.spinner(f"⏳ Membaca {sap_file.name}..."):
                    try:
                        df_up = load_excel(sap_file)
                        with st.spinner(f"💾 Menyimpan {len(df_up):,} baris..."):
                            cnt = bulk_replace_pr(df_up)
                        st.success(f"✅ {cnt:,} baris SAP PR berhasil diimport!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal: {e}")

    with col_tpl_sap:
        tpl_pr = pd.DataFrame(columns=[
            "Plnt","Purch.Req.","Item","Material","Material Description",
            "D","Rel","PGr","S","TrackingNo","Qty Requested","Un",
            "Req.Date","Valn Price","Crcy","Per","Release Dt"
        ])
        st.download_button("📋 Download Template",
                           data=to_excel_bytes(tpl_pr, "Template SAP PR"),
                           file_name="Template_SAP_PR.xlsx", key="pr_tpl")

    with col_exp_sap:
        df_sap_exp = fetch_sap_pr(search=sap_search, limit=50000)
        if not df_sap_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_sap_exp, "SAP PR"),
                               file_name=f"SAP_PR_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               key="sap_exp")

    df_sap = fetch_sap_pr(search=sap_search, limit=sap_limit)
    if df_sap.empty:
        st.info("📭 Belum ada data PR. Upload file Excel untuk memulai.")
    else:
        st.caption(f"Menampilkan {len(df_sap):,} dari {counts['pr']:,} baris")
        col_show = [c for c in [
            "id","plant","pr","item","material","material_description",
            "d","r","pgr","s","tracking_no","qty_pr","un","req_date",
            "valn_price","pr_curr","pr_per","release_date","tracking"
        ] if c in df_sap.columns]
        st.dataframe(df_sap[col_show], use_container_width=True, height=400, hide_index=True,
                     column_config={
                         "qty_pr": st.column_config.NumberColumn("Qty Requested"),
                         "valn_price": st.column_config.NumberColumn("Valn Price"),
                     })


# ════════════════════════════════════════════════════════════════
# TAB 7 — ORDER
# ════════════════════════════════════════════════════════════════
with tab_order:
    st.subheader("📋 Order")

    col1, col2 = st.columns([3, 1])
    with col1:
        ord_search = st.text_input("🔍 Cari", placeholder="Order, deskripsi, equipment...", key="ord_search")
    with col2:
        ord_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="ord_limit")

    col_ul_ord, col_tpl_ord, col_exp_ord = st.columns([1, 1, 1])
    with col_ul_ord:
        ord_file = st.file_uploader("📥 Upload Excel Order", type=["xlsx","xls","csv"], key="ord_upload")
        if ord_file:
            ord_mode = st.radio("Mode", ["Ganti Semua (Replace)"], key="ord_mode")
            if st.button("✅ Import Order", key="ord_import"):
                with st.spinner(f"⏳ Membaca {ord_file.name}..."):
                    try:
                        df_up = load_excel(ord_file)
                        with st.spinner(f"💾 Menyimpan {len(df_up):,} baris..."):
                            cnt = bulk_replace_order(df_up)
                        st.success(f"✅ {cnt:,} baris Order berhasil diimport!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal: {e}")

    with col_tpl_ord:
        tpl_ord = pd.DataFrame(columns=[
            "Plant","Order","Superior order","Notification","Created on","Description",
            "Revision","Equipment","System status","User status","Functional Loc.",
            "Location","WBS ord. header","Cost Center","TotalPlnndCosts",
            "Total act.costs","Planner group","Main WorkCtr","Entered by",
            "Changed by","Bas. start date","Basic fin. date","Actual release"
        ])
        st.download_button("📋 Download Template",
                           data=to_excel_bytes(tpl_ord, "Template Order"),
                           file_name="Template_Order.xlsx", key="ord_tpl")

    with col_exp_ord:
        df_ord_exp = fetch_order(search=ord_search, limit=50000)
        if not df_ord_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_ord_exp, "Order"),
                               file_name=f"Order_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               key="ord_exp")

    df_ord = fetch_order(search=ord_search, limit=ord_limit)
    if df_ord.empty:
        st.info("📭 Belum ada data Order. Upload file Excel untuk memulai.")
    else:
        st.caption(f"Menampilkan {len(df_ord):,} dari {counts['order']:,} baris")
        col_show = [c for c in [
            "plant","order","superior_order","notification","created_on","description",
            "revision","equipment","system_status","user_status","funct_location",
            "location","wbs_ord_header","cost_center","total_plan_cost","total_act_cost",
            "planner_group","main_work_ctr","entry_by","changed_by",
            "basic_start_date","basic_finish_date","actual_release"
        ] if c in df_ord.columns]
        st.dataframe(df_ord[col_show], use_container_width=True, height=400, hide_index=True,
                     column_config={
                         "total_plan_cost": st.column_config.NumberColumn("Total Plan Cost"),
                         "total_act_cost": st.column_config.NumberColumn("Total Act. Cost"),
                     })


# ════════════════════════════════════════════════════════════════
# TAB 8 — PO
# ════════════════════════════════════════════════════════════════
with tab_po:
    st.subheader("🛒 Purchase Order (PO)")

    col1, col2 = st.columns([3, 1])
    with col1:
        po_search = st.text_input("🔍 Cari", placeholder="PO, Purchreq, material...", key="po_search")
    with col2:
        po_limit = st.selectbox("Baris", [100, 500, 1000, 5000], key="po_limit")

    col_ul_po, col_tpl_po, col_exp_po = st.columns([1, 1, 1])
    with col_ul_po:
        po_file = st.file_uploader("📥 Upload Excel PO", type=["xlsx","xls","csv"], key="po_upload")
        if po_file:
            if st.button("✅ Import PO", key="po_import"):
                with st.spinner(f"⏳ Membaca {po_file.name}..."):
                    try:
                        df_up = load_excel(po_file)
                        with st.spinner(f"💾 Menyimpan {len(df_up):,} baris..."):
                            cnt = bulk_replace_po(df_up)
                        st.success(f"✅ {cnt:,} baris PO berhasil diimport!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal: {e}")

    with col_tpl_po:
        tpl_po = pd.DataFrame(columns=[
            "Plnt","Purchreq","Item","Material","Short_Text","PO","PO_Item",
            "D","DCI","PGr","Doc_Date","PO_Quantity","Qty_Delivered",
            "Deliv_Date","OUn","Net_Price","Crcy","Per"
        ])
        st.download_button("📋 Download Template",
                           data=to_excel_bytes(tpl_po, "Template PO"),
                           file_name="Template_PO.xlsx", key="po_tpl")

    with col_exp_po:
        df_po_exp = fetch_sap_po(search=po_search, limit=50000)
        if not df_po_exp.empty:
            st.download_button("📤 Export Excel",
                               data=to_excel_bytes(df_po_exp, "PO"),
                               file_name=f"PO_{datetime.now().strftime('%Y%m%d')}.xlsx",
                               key="po_exp")

    df_po = fetch_sap_po(search=po_search, limit=po_limit)
    if df_po.empty:
        st.info("📭 Belum ada data PO. Upload file Excel untuk memulai.")
    else:
        st.caption(f"Menampilkan {len(df_po):,} dari {counts['po']:,} baris")
        col_show = [c for c in [
            "plnt","purchreq","item","material","short_text","po","po_item",
            "d","dci","pgr","doc_date","po_quantity","qty_delivered",
            "deliv_date","oun","net_price","crcy","per"
        ] if c in df_po.columns]
        st.dataframe(df_po[col_show], use_container_width=True, height=400, hide_index=True,
                     column_config={
                         "po_quantity": st.column_config.NumberColumn("PO Quantity"),
                         "qty_delivered": st.column_config.NumberColumn("Qty Delivered"),
                         "net_price": st.column_config.NumberColumn("Net Price"),
                     })


# ════════════════════════════════════════════════════════════════
# TAB 9 — TRACKING
# ════════════════════════════════════════════════════════════════
with tab_tracking:
    st.subheader("🔍 End-to-End Procurement Tracking")

    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        trk_search = st.text_input("🔍 Cari", placeholder="Order, material, PR, PO...", key="trk_search")
    with col2:
        trk_status_filter = st.selectbox("Status", [
            "", "🔴 Belum PR", "🟡 PR Created", "🔵 PO Created",
            "🟠 Partial Delivery", "✅ Complete"
        ], key="trk_status")
    with col3:
        trk_limit = st.selectbox("Baris", [200, 500, 1000, 5000], key="trk_limit")

    # ── Build Tracking Data via SQL JOIN ──
    @st.cache_data(ttl=15)
    def build_tracking(search="", status_filter="", limit=500):
        sql = """
            SELECT
                t.plant, t.equipment, t."order", t.reservno, t.revision,
                t.material, t.itm, t.material_description,
                t.qty_reqmts, t.qty_stock,
                t.pr, t.item AS pr_item, t.qty_pr,
                t.cost_ctrs, t.sloc, t.del, t.fis, t.ict, t.pg,
                t.recipient, t.unloading_point, t.reqmts_date,
                t.qty_f_avail_check, t.qty_withdrawn, t.uom, t.gl_acct,
                t.res_price, t.res_per, t.res_curr,
                -- Order data
                wo.description, wo.superior_order, wo.notification, wo.created_on,
                wo.system_status, wo.user_status, wo.funct_location, wo.location,
                wo.wbs_ord_header, wo.cost_center, wo.total_plan_cost, wo.total_act_cost,
                wo.planner_group, wo.main_work_ctr, wo.entry_by, wo.changed_by,
                wo.basic_start_date, wo.basic_finish_date, wo.actual_release,
                -- PR data
                sp.req_date, sp.tracking_no,
                -- PO data
                po.po AS po_num, po.po_item, po.po_quantity, po.qty_delivered,
                po.deliv_date, po.net_price, po.crcy, po.doc_date
            FROM taex_reservasi t
            LEFT JOIN work_order wo ON wo."order" = t."order"
            LEFT JOIN sap_pr sp ON sp.pr = t.pr AND (sp.d IS NULL OR sp.d = '')
            LEFT JOIN sap_po po ON po.purchreq = t.pr AND (po.d IS NULL OR po.d = '')
            WHERE t.material IS NOT NULL AND t.material != ''
        """
        params = []
        if search:
            sql += """ AND (t.material ILIKE %s OR t.material_description ILIKE %s
                            OR t."order" ILIKE %s OR t.pr ILIKE %s OR po.po ILIKE %s)"""
            p = f"%{search}%"; params.extend([p, p, p, p, p])

        sql += f" LIMIT %s"
        params.append(limit)

        rows = query(sql, params)
        return pd.DataFrame([dict(r) for r in rows])

    df_trk = build_tracking(search=trk_search, limit=trk_limit)

    if df_trk.empty:
        st.info("📭 Tidak ada data tracking. Pastikan data TA-ex, Order, PR, dan PO sudah diupload.")
    else:
        # ── Hitung status per row ──
        def calc_status(row):
            has_pr = bool(row.get("pr"))
            has_po = bool(row.get("po_num"))
            qty_po = float(row.get("po_quantity") or 0)
            qty_del = float(row.get("qty_delivered") or 0)
            if not has_pr: return "no-pr"
            if not has_po: return "pr-created"
            if qty_del <= 0: return "po-created"
            if qty_del < qty_po: return "partial"
            return "complete"

        df_trk["status"] = df_trk.apply(calc_status, axis=1)

        # Filter status
        status_map = {
            "🔴 Belum PR": "no-pr", "🟡 PR Created": "pr-created",
            "🔵 PO Created": "po-created", "🟠 Partial Delivery": "partial", "✅ Complete": "complete"
        }
        if trk_status_filter and trk_status_filter in status_map:
            df_trk = df_trk[df_trk["status"] == status_map[trk_status_filter]]

        # ── Summary Cards ──
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        total_orders = df_trk["order"].nunique() if "order" in df_trk.columns else 0
        total_mat    = len(df_trk)
        has_pr_cnt   = (df_trk["pr"].notna() & (df_trk["pr"] != "")).sum() if "pr" in df_trk.columns else 0
        has_po_cnt   = (df_trk["po_num"].notna() & (df_trk["po_num"] != "")).sum() if "po_num" in df_trk.columns else 0
        partial_cnt  = (df_trk["status"] == "partial").sum()
        complete_cnt = (df_trk["status"] == "complete").sum()
        no_pr_cnt    = (df_trk["status"] == "no-pr").sum()
        total_nilai  = df_trk["net_price"].fillna(0).sum() if "net_price" in df_trk.columns else 0

        c1.markdown(card(total_orders, "Total Order", "#1a56db"), unsafe_allow_html=True)
        c2.markdown(card(total_mat, "Total Material", "#6d28d9"), unsafe_allow_html=True)
        c3.markdown(card(has_pr_cnt, "Sudah PR", "#0891b2"), unsafe_allow_html=True)
        c4.markdown(card(has_po_cnt, "Sudah PO", "#059669"), unsafe_allow_html=True)
        c5.markdown(card(partial_cnt, "Partial Delivery", "#d97706"), unsafe_allow_html=True)
        c6.markdown(card(complete_cnt, "Complete", "#16a34a"), unsafe_allow_html=True)
        c7.markdown(card(no_pr_cnt, "Belum PR", "#dc2626"), unsafe_allow_html=True)

        st.caption(f"Total Nilai PO: **Rp {total_nilai:,.0f}**")

        # ── Export ──
        if st.button("📤 Export Tracking Excel", key="trk_exp"):
            st.download_button(
                "💾 Download",
                data=to_excel_bytes(df_trk, "Tracking"),
                file_name=f"Tracking_{datetime.now().strftime('%Y%m%d')}.xlsx",
                key="trk_exp_dl"
            )

        st.caption(f"Menampilkan {len(df_trk):,} baris")
        col_show = [c for c in [
            "plant","equipment","order","reservno","revision","material","itm",
            "material_description","qty_reqmts","qty_stock","pr","pr_item","qty_pr",
            "del","fis","ict","pg","description","system_status",
            "basic_start_date","basic_finish_date",
            "req_date","po_num","po_item","po_quantity","qty_delivered",
            "deliv_date","net_price","crcy","status"
        ] if c in df_trk.columns]
        st.dataframe(df_trk[col_show], use_container_width=True, height=500, hide_index=True,
                     column_config={
                         "qty_reqmts": st.column_config.NumberColumn("Qty Reqmts"),
                         "qty_stock":  st.column_config.NumberColumn("Qty Stock"),
                         "qty_pr":     st.column_config.NumberColumn("Qty PR"),
                         "po_quantity":  st.column_config.NumberColumn("PO Qty"),
                         "qty_delivered": st.column_config.NumberColumn("Qty Delivered"),
                         "net_price":  st.column_config.NumberColumn("Net Price"),
                     })


# ════════════════════════════════════════════════════════════════
# TAB 10 — AUDIT
# ════════════════════════════════════════════════════════════════
with tab_audit:
    st.subheader("🔎 Audit — Cek Perubahan TA-ex vs PRISMA")

    AUDIT_COLS = [
        ("equipment", "Equipment"), ("reservno", "Reserv.No."), ("revision", "Revision"),
        ("material_description", "Material Description"), ("qty_reqmts", "Reqmt Qty"),
        ("del", "Del"), ("fis", "FIs"), ("ict", "ICt"), ("pg", "PG"),
        ("uom", "BUn"), ("recipient", "Recipient"), ("unloading_point", "Unloading Point"),
        ("reqmts_date", "Reqmt Date"),
    ]

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        aud_search = st.text_input("🔍 Cari", placeholder="Order, material...", key="aud_search")
    with col2:
        col_opts = [("", "Semua Kolom")] + [(k, v) for k, v in AUDIT_COLS]
        col_labels = [v for _, v in col_opts]
        col_keys   = [k for k, _ in col_opts]
        aud_col_sel = st.selectbox("Kolom berubah", col_labels, key="aud_col")
        aud_col_key = col_keys[col_labels.index(aud_col_sel)]
    with col3:
        aud_limit = st.selectbox("Baris", [100, 500, 1000], key="aud_limit")

    @st.cache_data(ttl=10)
    def fetch_audit(search="", col_filter="", limit=100):
        col_conditions = []
        if col_filter:
            target_cols = [(col_filter, next(v for k, v in AUDIT_COLS if k == col_filter))]
        else:
            target_cols = AUDIT_COLS

        unions = []
        for key, label in target_cols:
            p_val = f"COALESCE(p.{key}::text, '')"
            t_val = f"COALESCE(t.{key}::text, '')"
            unions.append(f"""
                SELECT t."order" AS order_val, t.material, t.itm,
                       '{key}' AS col_key, '{label}' AS col_label,
                       {p_val} AS val_prisma, {t_val} AS val_taex
                FROM prisma_reservasi p
                JOIN taex_reservasi t
                  ON p."order" = t."order"
                  AND p.material = t.material
                  AND p.itm = t.itm
                WHERE p.{key} IS DISTINCT FROM t.{key}
            """)
            if search:
                unions[-1] += f" AND (t.\"order\" ILIKE '%{search}%' OR t.material ILIKE '%{search}%')"

        if not unions:
            return pd.DataFrame()

        full_sql = " UNION ALL ".join(unions) + f" ORDER BY order_val, material, itm, col_key LIMIT {limit}"
        rows = query(full_sql)
        return pd.DataFrame([dict(r) for r in rows])

    # Count stats
    count_sql = " UNION ALL ".join([f"""
        SELECT COUNT(*) AS c FROM prisma_reservasi p
        JOIN taex_reservasi t ON p."order"=t."order" AND p.material=t.material AND p.itm=t.itm
        WHERE p.{k} IS DISTINCT FROM t.{k}
    """ for k, _ in AUDIT_COLS])
    # Simplified count
    changed_rows_sql = """
        SELECT COUNT(DISTINCT (t."order", t.material, t.itm)) AS c
        FROM prisma_reservasi p
        JOIN taex_reservasi t ON p."order"=t."order" AND p.material=t.material AND p.itm=t.itm
        WHERE """ + " OR ".join([f"p.{k} IS DISTINCT FROM t.{k}" for k, _ in AUDIT_COLS])

    try:
        changed_res = query(changed_rows_sql)
        changed_count = int(changed_res[0]["c"]) if changed_res else 0
    except:
        changed_count = 0

    st.markdown(info_bar([
        ("Baris TA-ex", f"{counts['taex']:,}"),
        ("Baris PRISMA", f"{counts['prisma']:,}"),
        ("Baris Berubah", str(changed_count)),
    ]), unsafe_allow_html=True)

    if changed_count == 0:
        st.success("✅ Tidak ada perbedaan — data TA-ex dan PRISMA konsisten!")
    else:
        df_audit = fetch_audit(search=aud_search, col_filter=aud_col_key, limit=aud_limit)
        if df_audit.empty:
            st.info("Tidak ada hasil untuk filter ini.")
        else:
            st.caption(f"Menampilkan {len(df_audit):,} perbedaan")
            st.dataframe(
                df_audit.rename(columns={
                    "order_val": "Order", "col_label": "Kolom",
                    "val_prisma": "Nilai di PRISMA", "val_taex": "Nilai di TA-ex"
                }),
                use_container_width=True, height=400, hide_index=True,
            )
            # Export
            st.download_button(
                "📤 Export Audit Excel",
                data=to_excel_bytes(df_audit, "Audit"),
                file_name=f"Audit_TAex_PRISMA_{datetime.now().strftime('%Y%m%d')}.xlsx",
                key="aud_exp"
            )


# ════════════════════════════════════════════════════════════════
# TAB 11 — RESET
# ════════════════════════════════════════════════════════════════
with tab_reset:
    st.subheader("⚠️ Reset Semua Data")
    st.error("""
    **PERINGATAN**: Tindakan ini akan menghapus SEMUA data dari seluruh tabel
    (taex_reservasi, prisma_reservasi, kumpulan_summary, sap_pr, sap_po, work_order, app_state).
    Tindakan ini **tidak bisa dibatalkan**.
    """)

    confirm_text = st.text_input(
        "Ketik **RESET** untuk konfirmasi:",
        placeholder="Ketik RESET di sini",
        key="reset_confirm"
    )

    if st.button("🗑 Reset Semua Data", type="primary", key="do_reset"):
        if confirm_text.strip().upper() == "RESET":
            with st.spinner("⏳ Mereset semua data..."):
                try:
                    for tbl in ["taex_reservasi", "prisma_reservasi", "kumpulan_summary",
                                "sap_pr", "sap_po", "work_order", "app_state"]:
                        execute(f"DELETE FROM {tbl}")
                    for seq in ["taex_reservasi_id_seq", "prisma_reservasi_id_seq",
                                "kumpulan_summary_id_seq", "sap_pr_id_seq",
                                "sap_po_id_seq", "work_order_id_seq"]:
                        try:
                            execute(f"ALTER SEQUENCE {seq} RESTART WITH 1")
                        except Exception:
                            pass
                    st.session_state.kk_data = []
                    st.session_state.kk_code = None
                    st.session_state.summary_data = []
                    st.cache_data.clear()
                    st.success("✅ Semua data telah direset!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal reset: {e}")
        else:
            st.warning("Ketik RESET (huruf kapital) untuk konfirmasi.")