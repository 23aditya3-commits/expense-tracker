import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# -------------------------------
# PAGE CONFIG (MOBILE FRIENDLY)
# -------------------------------
st.set_page_config(
    page_title="Expense Tracker",
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
# TITLE
# -------------------------------
st.title("💰 Expense Tracker")

# -------------------------------
# 📅 MONTH SELECTOR (MOBILE SAFE)
# -------------------------------
months = [(datetime.now().replace(day=1) - pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(6)]
months = sorted(months, reverse=True)

month_map = {m: datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months}
reverse_map = {v: k for k, v in month_map.items()}

selected_display = st.selectbox("Month", list(month_map.values()))
selected_month = reverse_map[selected_display]

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
            (amount, category, payment_mode, str(exp_date), note)
        )
        conn.commit()
        st.rerun()
    else:
        st.warning("Enter amount")

st.divider()

# -------------------------------
# 📊 DATA
# -------------------------------
df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    df['date'] = pd.to_datetime(df['date'])
    monthly_df = df[df['date'].dt.to_period("M").astype(str) == selected_month]

    # -------------------------------
    # 💳 PAYMENT TABLE (NO SCROLL)
    # -------------------------------
    st.subheader("💳 Payments")

    all_modes = ["Cash","Amazon","Ixiago","Jupiter","TataNeu","SBI","Mom","ICICI","Swiggy"]

    monthly_df["amount"] = pd.to_numeric(monthly_df["amount"], errors="coerce").fillna(0)

    pivot = (
        monthly_df.groupby("payment_mode")["amount"]
        .sum()
        .reindex(all_modes, fill_value=0)
        .to_frame().T
    )

    pivot = pivot.astype(int)

    st.table(pivot)  # ✅ mobile fit

    st.divider()

    # -------------------------------
    # 📊 SUMMARY
    # -------------------------------
    st.subheader("📊 Summary")

    total = monthly_df["amount"].sum()
    remaining = remaining_budget - total

    st.metric("Spent", f"₹ {total}")
    st.metric("Left", f"₹ {remaining}")

    if not monthly_df.empty:
        st.dataframe(monthly_df.sort_values(by="date", ascending=False), use_container_width=True)
    else:
        st.info("No data")

else:
    st.info("No expenses yet")
