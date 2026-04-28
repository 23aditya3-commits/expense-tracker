import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="Expense Tracker", layout="centered")

# -------------------------------
# DB SETUP
# -------------------------------
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()

# Expenses table
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

# Settings table (MONTH-WISE)
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
# 📅 MONTH SELECTOR (TOP)
# -------------------------------
current_month = datetime.now().strftime("%Y-%m")

# Get months from DB
df_all = pd.read_sql("SELECT * FROM expenses", conn)

if not df_all.empty:
    df_all['date'] = pd.to_datetime(df_all['date'])
    months = sorted(df_all['date'].dt.to_period("M").astype(str).unique(), reverse=True)
    if current_month not in months:
        months.insert(0, current_month)
else:
    months = [current_month]

selected_month = st.selectbox("📅 Select Month", months, index=0)

st.divider()

# -------------------------------
# 💰 LOAD MONTHLY BUDGET
# -------------------------------
settings = c.execute("SELECT * FROM settings WHERE month=?", (selected_month,)).fetchone()

if settings:
    income_db, invest_db, home_db, emi_db = settings[1], settings[2], settings[3], settings[4]
else:
    income_db, invest_db, home_db, emi_db = 0, 0, 0, 0

# -------------------------------
# 💰 MONTHLY BUDGET
# -------------------------------
st.subheader(f"💰 Budget for {selected_month}")

col1, col2 = st.columns(2)

with col1:
    income = st.number_input("Monthly Income", value=income_db)
    investments = st.number_input("Investments", value=invest_db)

with col2:
    sent_home = st.number_input("Sent to Home", value=home_db)
    emi = st.number_input("EMI", value=emi_db)

remaining_budget = income - (investments + sent_home + emi)

st.success(f"💸 Remaining Budget: ₹ {remaining_budget}")

# Save
if st.button("💾 Save Budget"):
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
    st.success("✅ Budget Saved!")

st.divider()

# -------------------------------
# 🧾 ADD EXPENSE
# -------------------------------
st.subheader("🧾 Add Expense")

exp_date = st.date_input("Date", date.today())

payment_mode = st.selectbox("Mode of Payment", [
    "Cash/Kotak","Amazonpay CC","Ixiago CC","Jupiter CC",
    "Tata Neu CC","Sbi CC","Mom Kotak","Icici CC","Swiggy CC"
])

category = st.selectbox("Category", [
    "Grocery","Pets","Dress","Entertainment","Education",
    "Misc","Food","Rent","Others"
])

amount = st.number_input("Amount", min_value=0)
note = st.text_input("Note")

if st.button("Add Expense"):
    if amount > 0:
        c.execute(
            "INSERT INTO expenses (amount, category, payment_mode, date, note) VALUES (?, ?, ?, ?, ?)",
            (amount, category, payment_mode, str(exp_date), note)
        )
        conn.commit()
        st.success("✅ Expense Added!")
    else:
        st.warning("Enter valid amount")

st.divider()

# -------------------------------
# 📊 MONTHLY SUMMARY
# -------------------------------
st.subheader(f"📊 Summary for {selected_month}")

df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    df['date'] = pd.to_datetime(df['date'])

    monthly_df = df[df['date'].dt.to_period("M").astype(str) == selected_month]

    total_spent = monthly_df['amount'].sum()
    remaining_after = remaining_budget - total_spent

    st.metric("💸 Spent", f"₹ {total_spent}")
    st.metric("💰 Remaining", f"₹ {remaining_after}")

    # Alerts
    if remaining_after < 0:
        st.error("🚨 Budget exceeded!")
    elif remaining_after < remaining_budget * 0.2:
        st.warning("⚠️ 80% budget used")

    st.dataframe(monthly_df.sort_values(by="date", ascending=False))

    if not monthly_df.empty:
        # Category chart
        st.subheader("📊 Category Breakdown")
        st.bar_chart(monthly_df.groupby("category")["amount"].sum())

        # Payment chart
        st.subheader("💳 Payment Mode Usage")
        st.bar_chart(monthly_df.groupby("payment_mode")["amount"].sum())

        # Daily trend
        st.subheader("📈 Daily Trend")
        st.line_chart(monthly_df.groupby("date")["amount"].sum())

else:
    st.info("No expenses yet")
