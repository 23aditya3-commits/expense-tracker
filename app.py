import streamlit as st
import pandas as pd
from datetime import date, datetime
from google.oauth2.service_account import Credentials
import json
import plotly.graph_objects as go
import gspread

# -------------------------------
# PAGE CONFIG (MOBILE FRIENDLY)
# -------------------------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="centered"
)

# -------------------------------
# 🔑 GOOGLE SHEETS CONNECTION
# -------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
@st.cache_resource
def get_sheet():
    creds_dict = {
        "type": st.secrets["gcp"]["type"],
        "project_id": st.secrets["gcp"]["project_id"],
        "private_key_id": st.secrets["gcp"]["private_key_id"],
        "private_key": st.secrets["gcp"]["private_key"],
        "client_email": st.secrets["gcp"]["client_email"],
        "client_id": st.secrets["gcp"]["client_id"],
        "auth_uri": st.secrets["gcp"]["auth_uri"],
        "token_uri": st.secrets["gcp"]["token_uri"],
    }
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(st.secrets["sheets"]["sheet_name"])

sheet = get_sheet()

# -------------------------------
# 📋 SHEET HELPERS
# -------------------------------

def get_ws(name):
    headers_map = {
        "expenses": ["id", "amount", "category", "payment_mode", "date", "note"],
        "settings": ["month", "income", "investments", "sent_home", "emi"],
        "app_meta": ["key", "value"]
    }
    ws_list = [w.title for w in sheet.worksheets()]
    if name not in ws_list:
        ws = sheet.add_worksheet(title=name, rows=1000, cols=20)
        ws.append_row(headers_map[name])
        return ws
    return sheet.worksheet(name)

# -------------------------------
# 💾 SESSION STATE CACHE
# Fetch from Sheets only when needed, store in session_state
# This prevents hitting the 60 reads/min quota
# -------------------------------

def refresh_cache():
    """Force re-fetch all data from Google Sheets into session_state."""
    ws_exp = get_ws("expenses")
    data = ws_exp.get_all_records()
    st.session_state["cache_expenses"] = pd.DataFrame(
        data if data else [],
        columns=["id", "amount", "category", "payment_mode", "date", "note"]
    )

    ws_set = get_ws("settings")
    data = ws_set.get_all_records()
    st.session_state["cache_settings"] = pd.DataFrame(
        data if data else [],
        columns=["month", "income", "investments", "sent_home", "emi"]
    )

def get_cached_expenses():
    if "cache_expenses" not in st.session_state:
        refresh_cache()
    return st.session_state["cache_expenses"]

def get_cached_settings():
    if "cache_settings" not in st.session_state:
        refresh_cache()
    return st.session_state["cache_settings"]

# ---- EXPENSES ----

def load_expenses():
    return get_cached_expenses()

def add_expense(amount, category, payment_mode, exp_date, note):
    ws = get_ws("expenses")
    df = get_cached_expenses()
    new_id = int(df["id"].max()) + 1 if not df.empty and df["id"].notna().any() else 1
    ws.append_row([new_id, amount, category, payment_mode, exp_date, note])
    # Update cache locally without re-fetching
    new_row = pd.DataFrame([[new_id, amount, category, payment_mode, exp_date, note]],
                           columns=["id", "amount", "category", "payment_mode", "date", "note"])
    st.session_state["cache_expenses"] = pd.concat(
        [st.session_state["cache_expenses"], new_row], ignore_index=True
    )

def delete_expenses_for_month(month_str):
    ws = get_ws("expenses")
    all_vals = ws.get_all_values()
    if len(all_vals) <= 1:
        return
    headers = all_vals[0]
    date_col = headers.index("date")
    rows_to_delete = []
    for i, row in enumerate(all_vals[1:], start=2):
        if len(row) > date_col and row[date_col].startswith(month_str):
            rows_to_delete.append(i)
    for row_idx in reversed(rows_to_delete):
        ws.delete_rows(row_idx)
    refresh_cache()

def delete_all_expenses():
    ws = get_ws("expenses")
    ws.clear()
    ws.append_row(["id", "amount", "category", "payment_mode", "date", "note"])
    refresh_cache()

# ---- SETTINGS ----

def load_settings():
    return get_cached_settings()

def get_settings_for_month(month_str):
    df = get_cached_settings()
    if df.empty:
        return None
    row = df[df["month"].astype(str) == month_str]
    if row.empty:
        return None
    r = row.iloc[0]
    return (r["month"], float(r["income"]), float(r["investments"]), float(r["sent_home"]), float(r["emi"]))

def upsert_settings(month_str, income, investments, sent_home, emi):
    ws = get_ws("settings")
    all_vals = ws.get_all_values()
    if len(all_vals) <= 1:
        ws.append_row([month_str, income, investments, sent_home, emi])
    else:
        headers = all_vals[0]
        month_col = headers.index("month")
        updated = False
        for i, row in enumerate(all_vals[1:], start=2):
            if len(row) > month_col and row[month_col] == month_str:
                ws.update(f"A{i}:E{i}", [[month_str, income, investments, sent_home, emi]])
                updated = True
                break
        if not updated:
            ws.append_row([month_str, income, investments, sent_home, emi])

    # Update cache locally
    df = get_cached_settings().copy()
    df["month"] = df["month"].astype(str)
    if month_str in df["month"].values:
        df.loc[df["month"] == month_str, ["income","investments","sent_home","emi"]] = [income, investments, sent_home, emi]
    else:
        new_row = pd.DataFrame([[month_str, income, investments, sent_home, emi]],
                               columns=["month","income","investments","sent_home","emi"])
        df = pd.concat([df, new_row], ignore_index=True)
    st.session_state["cache_settings"] = df

def delete_settings_for_month(month_str):
    ws = get_ws("settings")
    all_vals = ws.get_all_values()
    if len(all_vals) <= 1:
        return
    headers = all_vals[0]
    month_col = headers.index("month")
    for i, row in enumerate(all_vals[1:], start=2):
        if len(row) > month_col and row[month_col] == month_str:
            ws.delete_rows(i)
            break
    refresh_cache()

def delete_all_settings():
    ws = get_ws("settings")
    ws.clear()
    ws.append_row(["month", "income", "investments", "sent_home", "emi"])
    refresh_cache()

# ---- APP META ----
# Meta is tiny (1-2 rows), read directly — no caching needed

def get_meta(key):
    ws = get_ws("app_meta")
    data = ws.get_all_records()
    for row in data:
        if row["key"] == key:
            return str(row["value"])
    return None

def set_meta(key, value):
    ws = get_ws("app_meta")
    all_vals = ws.get_all_values()
    if len(all_vals) <= 1:
        ws.append_row([key, value])
        return
    headers = all_vals[0]
    key_col = headers.index("key")
    for i, row in enumerate(all_vals[1:], start=2):
        if len(row) > key_col and row[key_col] == key:
            ws.update(f"A{i}:B{i}", [[key, value]])
            return
    ws.append_row([key, value])

# -------------------------------
# 🗓️ NEW MONTH AUTO-RESET
# Runs only once per session via session_state flag
# -------------------------------
today = datetime.now()
current_month_str = today.strftime("%Y-%m")

if "month_check_done" not in st.session_state:
    last_seen = get_meta("last_seen_month")

    if last_seen is None:
        set_meta("last_seen_month", current_month_str)

    elif last_seen != current_month_str:
        existing_new = get_settings_for_month(current_month_str)
        if not existing_new:
            last_settings = get_settings_for_month(last_seen)
            if last_settings:
                upsert_settings(
                    current_month_str,
                    last_settings[1], last_settings[2],
                    last_settings[3], last_settings[4]
                )
        set_meta("last_seen_month", current_month_str)
        st.toast(f"🎉 New month! Budget carried forward from {last_seen}.", icon="📅")

    st.session_state["month_check_done"] = True

# -------------------------------
# TITLE
# -------------------------------
st.title("💰 Expense Tracker")

# -------------------------------
# 📅 MONTH + YEAR SELECTOR
# -------------------------------
if "selected_month" not in st.session_state:
    st.session_state.selected_month = datetime.now().month

if "selected_year" not in st.session_state:
    st.session_state.selected_year = datetime.now().year

col_m, col_y = st.columns(2)

months_list = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

years_list = list(range(2024, 2037))

with col_m:
    selected_month_name = st.selectbox(
        "Month",
        months_list,
        index=st.session_state.selected_month - 1
    )

with col_y:
    selected_year = st.selectbox(
        "Year",
        years_list,
        index=years_list.index(st.session_state.selected_year)
    )

st.session_state.selected_month = months_list.index(selected_month_name) + 1
st.session_state.selected_year = selected_year

month_number = st.session_state.selected_month
selected_year = st.session_state.selected_year

selected_month = f"{selected_year}-{month_number:02d}"
selected_display = f"{selected_month_name} {selected_year}"

st.divider()

# -------------------------------
# LOAD SETTINGS
# -------------------------------
settings = get_settings_for_month(selected_month)
income_db, invest_db, home_db, emi_db = (settings[1:5] if settings else (0, 0, 0, 0))

# -------------------------------
# 💰 BUDGET
# -------------------------------
st.subheader(f"💰 {selected_display} Budget")

col1, col2 = st.columns(2)

with col1:
    income = st.number_input("Income", value=income_db if income_db != 0 else None, placeholder="₹")
    investments = st.number_input("Invest", value=invest_db if invest_db != 0 else None, placeholder="₹")

with col2:
    sent_home = st.number_input("Home", value=home_db if home_db != 0 else None, placeholder="₹")
    emi = st.number_input("EMI", value=emi_db if emi_db != 0 else None, placeholder="₹")

income = income or 0
investments = investments or 0
sent_home = sent_home or 0
emi = emi or 0

# Accurate "left" from cached expenses
_all_exp = load_expenses()
if not _all_exp.empty and "date" in _all_exp.columns:
    _monthly_now = _all_exp[_all_exp["date"].astype(str).str.startswith(selected_month)]
    total_spent_now = pd.to_numeric(_monthly_now["amount"], errors="coerce").sum()
else:
    total_spent_now = 0.0

remaining_budget = income - (investments + sent_home + emi)
remaining_after_expenses = remaining_budget - total_spent_now

st.success(f"💸 Spendable: ₹{remaining_budget:,.0f}  |  After expenses: ₹{remaining_after_expenses:,.0f}")

col_save, col_reset = st.columns(2)

with col_save:
    if st.button("💾 Save"):
        upsert_settings(selected_month, income, investments, sent_home, emi)
        st.success("Saved ✅")

with col_reset:
    if st.button("🗑 Reset"):
        st.session_state.confirm = True

if st.session_state.get("confirm"):
    st.warning("Reset this month?")

    col_yes, col_no = st.columns(2)

    with col_yes:
        if st.button("Yes"):
            delete_settings_for_month(selected_month)
            delete_expenses_for_month(selected_month)
            st.session_state.confirm = False
            st.rerun()

    with col_no:
        if st.button("No"):
            st.session_state.confirm = False
            st.rerun()

st.divider()

# -------------------------------
# 🧾 ADD EXPENSE
# -------------------------------
st.subheader("➕ Add Expense")

col1, col2 = st.columns(2)

with col1:
    exp_date = st.date_input("Date", date.today())
    category = st.selectbox("Category", [
        "Grocery", "Pets", "Dress", "Fun", "Edu", "Misc", "Food", "Rent", "Other"
    ])

with col2:
    payment_mode = st.selectbox("Mode", [
        "Cash", "Amazon", "Ixiago", "Jupiter", "TataNeu", "SBI", "Mom", "ICICI", "Swiggy"
    ])
    amount = st.number_input("Amount", value=None, placeholder="₹", min_value=0)

note = st.text_input("Note")

if st.button("Add"):
    if amount and amount > 0:
        add_expense(amount, category, payment_mode, exp_date.strftime("%Y-%m-%d"), note or "")
        st.rerun()
    else:
        st.warning("Enter amount")

st.divider()

# -------------------------------
# 📥 BACKUP DOWNLOAD
# -------------------------------
st.subheader("📥 Backup")

if st.button("📦 Generate Backup"):
    try:
        exp_df = load_expenses()
        set_df = load_settings()

        # Convert all columns to string-safe types before JSON serialization
        exp_df = exp_df.copy()
        exp_df["date"] = exp_df["date"].astype(str)

        backup_data = {
            "expenses": exp_df.to_dict(orient="records"),
            "settings": set_df.to_dict(orient="records")
        }
        st.download_button(
            label="⬇️ Download Full Backup",
            data=json.dumps(backup_data),
            file_name="expense_backup.json",
            mime="application/json"
        )
    except Exception as e:
        st.error(f"Backup failed: {e}")

# -------------------------------
# ♻️ RESTORE
# -------------------------------
st.subheader("♻️ Restore Backup")

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

uploaded_file = st.file_uploader("Upload backup.json", type=["json"], key=f"file_uploader_{st.session_state.uploader_key}")

if uploaded_file is not None:
    backup_data = json.load(uploaded_file)

    st.warning("⚠️ This will overwrite ALL data!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirm Restore"):
            try:
                delete_all_expenses()
                delete_all_settings()

                ws_exp = get_ws("expenses")
                for row in backup_data.get("expenses", []):
                    ws_exp.append_row([
                        row["id"], row["amount"], row["category"],
                        row["payment_mode"], row["date"], row.get("note", "")
                    ])

                ws_set = get_ws("settings")
                for row in backup_data.get("settings", []):
                    ws_set.append_row([
                        row["month"], row["income"], row["investments"],
                        row["sent_home"], row["emi"]
                    ])

                refresh_cache()
                st.success("✅ Full data restored!")
                st.session_state.uploader_key += 1  # forces file uploader to reset
                st.rerun()

            except Exception as e:
                st.error(f"Restore failed: {e}")

    with col2:
        if st.button("❌ Cancel Restore"):
            st.info("Restore cancelled")

st.divider()

# -------------------------------
# 📊 DATA
# -------------------------------
df = load_expenses()

if not df.empty:
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d", errors='coerce')
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    bad_rows = df[df['date'].isna()]
    if not bad_rows.empty:
        st.error("⚠️ Invalid date rows detected")
        st.write(bad_rows)

    monthly_df = df[df['date'].dt.to_period("M").astype(str) == selected_month].copy()

    st.subheader("💳 Payments")

    all_modes = ["Cash", "Amazon", "Ixiago", "Jupiter", "TataNeu", "SBI", "Mom", "ICICI", "Swiggy"]

    pivot = (
        monthly_df.groupby("payment_mode")["amount"]
        .sum()
        .reindex(all_modes, fill_value=0)
        .to_frame().T
    )

    pivot = pivot.astype(int)
    st.table(pivot)

    st.divider()

    st.subheader("📊 Summary")

    total = monthly_df["amount"].sum()
    remaining = remaining_budget - total

    st.metric("Spent", f"₹ {total:,.0f}")
    st.metric("Left", f"₹ {remaining:,.0f}")

    if not monthly_df.empty:
        st.dataframe(monthly_df.sort_values(by="date", ascending=False), use_container_width=True)
    else:
        st.info("No data")

    # -------------------------------
    # 📊 MONTHLY BAR CHART
    # -------------------------------
    st.divider()
    st.subheader("📊 Monthly Overview (Income vs Total Spend)")

    set_df = load_settings()

    if not set_df.empty:
        df['month'] = df['date'].dt.to_period("M").astype(str)
        expense_summary = df.groupby("month")["amount"].sum().reset_index()

        for col in ["income", "investments", "emi", "sent_home"]:
            set_df[col] = pd.to_numeric(set_df[col], errors="coerce").fillna(0)

        merged = pd.merge(set_df, expense_summary, on="month", how="left")
        merged["amount"] = merged["amount"].fillna(0)

        merged["total_spend"] = (
            merged["amount"] +
            merged["investments"] +
            merged["emi"] +
            merged["sent_home"]
        )

        merged["month_name"] = pd.to_datetime(merged["month"]).dt.strftime("%b %Y")
        merged = merged.sort_values("month")

        fig = go.Figure()

        fig.add_bar(
            x=merged["month_name"],
            y=merged["income"],
            name="Income 💰"
        )

        fig.add_bar(
            x=merged["month_name"],
            y=merged["total_spend"],
            name="Total Spend 💸"
        )

        fig.update_layout(
            barmode='group',
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            legend_title="",
            height=350,
            xaxis=dict(tickangle=-45)
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No monthly data available")

else:
    st.info("No expenses yet")
