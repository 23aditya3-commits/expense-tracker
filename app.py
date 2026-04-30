import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import json
import plotly.graph_objects as go

# -------------------------------
# PAGE CONFIG (MOBILE FRIENDLY)
# -------------------------------
st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="centered"
)

# -------------------------------
# DB SETUP
# -------------------------------
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL,
    category TEXT,
    payment_mode TEXT,
    date TEXT,
    note TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    month TEXT PRIMARY KEY,
    income REAL,
    investments REAL,
    sent_home REAL,
    emi REAL
)
""")

conn.commit()

# -------------------------------
# 🔁 AUTO BACKUP (FULL DATA)
# -------------------------------
def auto_backup():
    try:
        expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
        settings_df = pd.read_sql("SELECT * FROM settings", conn)

        backup_data = {
            "expenses": expenses_df.to_dict(orient="records"),
            "settings": settings_df.to_dict(orient="records")
        }

        with open("backup.json", "w") as f:
            json.dump(backup_data, f)
    except:
        pass

auto_backup()

# -------------------------------
# TITLE
# -------------------------------
st.title("💰 Expense Tracker")

# -------------------------------
# 📅 MONTH + YEAR SELECTOR (FIXED + SESSION LOCK)
# -------------------------------
if "selected_month" not in st.session_state:
    st.session_state.selected_month = datetime.now().month

if "selected_year" not in st.session_state:
    st.session_state.selected_year = datetime.now().year

col_m, col_y = st.columns(2)

months_list = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
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

# store back
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
settings = c.execute("SELECT * FROM settings WHERE month=?", (selected_month,)).fetchone()
income_db, invest_db, home_db, emi_db = (settings[1:5] if settings else (0,0,0,0))

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

remaining_budget = income - (investments + sent_home + emi)
st.success(f"💸 Left: ₹ {remaining_budget}")

col_save, col_reset = st.columns(2)

# SAVE
with col_save:
    if st.button("💾 Save"):
        c.execute("""
        INSERT INTO settings (month, income, investments, sent_home, emi)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
        income=excluded.income,
        investments=excluded.investments,
        sent_home=excluded.sent_home,
        emi=excluded.emi
        """, (selected_month, income, investments, sent_home, emi))
        conn.commit()
        st.success("Saved")

# RESET
with col_reset:
    if st.button("🗑 Reset"):
        st.session_state.confirm = True

if st.session_state.get("confirm"):
    st.warning("Reset this month?")

    col_yes, col_no = st.columns(2)

    with col_yes:
        if st.button("Yes"):
            c.execute("DELETE FROM settings WHERE month=?", (selected_month,))
            c.execute("DELETE FROM expenses WHERE strftime('%Y-%m', date)=?", (selected_month,))
            conn.commit()
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
        "Grocery","Pets","Dress","Fun","Edu","Misc","Food","Rent","Other"
    ])

with col2:
    payment_mode = st.selectbox("Mode", [
        "Cash","Amazon","Ixiago","Jupiter","TataNeu","SBI","Mom","ICICI","Swiggy"
    ])
    amount = st.number_input("Amount", value=None, placeholder="₹", min_value=0)

note = st.text_input("Note")

if st.button("Add"):
    if amount and amount > 0:
        c.execute(
            "INSERT INTO expenses (amount, category, payment_mode, date, note) VALUES (?, ?, ?, ?, ?)",
            (amount, category, payment_mode, exp_date.strftime("%Y-%m-%d"), note)  # FIXED
        )
        conn.commit()
        st.rerun()
    else:
        st.warning("Enter amount")

st.divider()

# -------------------------------
# 📥 BACKUP DOWNLOAD
# -------------------------------
st.subheader("📥 Backup")

try:
    with open("backup.json", "rb") as f:
        st.download_button(
            label="⬇️ Download Full Backup",
            data=f,
            file_name="expense_backup.json",
            mime="application/json"
        )
except:
    st.info("No backup available")

# -------------------------------
# ♻️ RESTORE
# -------------------------------
st.subheader("♻️ Restore Backup")

uploaded_file = st.file_uploader("Upload backup.json", type=["json"])

if uploaded_file is not None:
    backup_data = json.load(uploaded_file)

    st.warning("⚠️ This will overwrite ALL data!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirm Restore"):
            try:
                c.execute("DELETE FROM expenses")
                c.execute("DELETE FROM settings")

                for row in backup_data.get("expenses", []):
                    c.execute(
                        "INSERT INTO expenses (id, amount, category, payment_mode, date, note) VALUES (?, ?, ?, ?, ?, ?)",
                        (row["id"], row["amount"], row["category"], row["payment_mode"], row["date"], row["note"])
                    )

                for row in backup_data.get("settings", []):
                    c.execute(
                        "INSERT INTO settings (month, income, investments, sent_home, emi) VALUES (?, ?, ?, ?, ?)",
                        (row["month"], row["income"], row["investments"], row["sent_home"], row["emi"])
                    )

                conn.commit()
                st.success("✅ Full data restored!")
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
df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%d", errors='coerce')  # FIXED

    # DEBUG invalid dates
    bad_rows = df[df['date'].isna()]
    if not bad_rows.empty:
        st.error("⚠️ Invalid date rows detected")
        st.write(bad_rows)

    monthly_df = df[df['date'].dt.to_period("M").astype(str) == selected_month]

    st.subheader("💳 Payments")

    all_modes = ["Cash","Amazon","Ixiago","Jupiter","TataNeu","SBI","Mom","ICICI","Swiggy"]

    monthly_df = monthly_df.copy()  # FIXED
    monthly_df["amount"] = pd.to_numeric(monthly_df["amount"], errors="coerce").fillna(0)

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

    st.metric("Spent", f"₹ {total}")
    st.metric("Left", f"₹ {remaining}")

    if not monthly_df.empty:
        st.dataframe(monthly_df.sort_values(by="date", ascending=False), use_container_width=True)
    else:
        st.info("No data")

    # -------------------------------
    # 📊 MONTHLY BAR CHART
    # -------------------------------
    st.divider()
    st.subheader("📊 Monthly Overview (Income vs Total Spend)")

    exp_df = pd.read_sql("SELECT * FROM expenses", conn)
    set_df = pd.read_sql("SELECT * FROM settings", conn)

    if not set_df.empty:

        exp_df['date'] = pd.to_datetime(exp_df['date'], format="%Y-%m-%d", errors='coerce')  # FIXED
        exp_df['month'] = exp_df['date'].dt.to_period("M").astype(str)

        expense_summary = exp_df.groupby("month")["amount"].sum().reset_index()

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
