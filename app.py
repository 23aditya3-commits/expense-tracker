import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# -------------------------------
# PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="Expense Tracker", layout="centered")

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

# Ensure column exists (safe for old DB)
try:
    c.execute("ALTER TABLE expenses ADD COLUMN payment_mode TEXT")
    conn.commit()
except:
    pass

# -------------------------------
# TITLE
# -------------------------------
st.title("💰 Expense Tracker")

# -------------------------------
# SESSION STATE (PREVENT RESET)
# -------------------------------
for key in ["income", "investments", "sent_home", "emi"]:
    if key not in st.session_state:
        st.session_state[key] = 0

# -------------------------------
# 💰 MONTHLY BUDGET
# -------------------------------
st.subheader("💰 Monthly Budget Planner")

income = st.number_input("Monthly Income", value=st.session_state.income)
investments = st.number_input("Investments", value=st.session_state.investments)
sent_home = st.number_input("Sent to Home", value=st.session_state.sent_home)
emi = st.number_input("EMI", value=st.session_state.emi)

# Save values
st.session_state.income = income
st.session_state.investments = investments
st.session_state.sent_home = sent_home
st.session_state.emi = emi

remaining_budget = income - (investments + sent_home + emi)

st.success(f"💸 Remaining Budget for Expenses: ₹ {remaining_budget}")

st.divider()

# -------------------------------
# 🧾 ADD EXPENSE
# -------------------------------
st.subheader("🧾 Add Expense")

exp_date = st.date_input("Date", date.today())

payment_mode = st.selectbox("Mode of Payment", [
    "Cash/Kotak",
    "Amazonpay CC",
    "Ixiago CC",
    "Jupiter CC",
    "Tata Neu CC",
    "Sbi CC",
    "Mom Kotak",
    "Icici CC",
    "Swiggy CC"
])

category = st.selectbox("Category", [
    "Grocery",
    "Pets",
    "Dress",
    "Entertainment",
    "Education",
    "Misc",
    "Food",
    "Rent",
    "Others"
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
        st.warning("⚠️ Enter valid amount")

st.divider()

# -------------------------------
# 📊 MONTHLY SUMMARY + DASHBOARD
# -------------------------------
st.subheader("📊 Monthly Summary")

df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    df['date'] = pd.to_datetime(df['date'])

    # Get all months
    months = sorted(df['date'].dt.to_period("M").astype(str).unique(), reverse=True)

    # Default to latest month
    selected_month = st.selectbox("Select Month", months, index=0)

    # Filter data
    monthly_df = df[df['date'].dt.to_period("M").astype(str) == selected_month]

    total_spent = monthly_df['amount'].sum()
    remaining_after_spend = remaining_budget - total_spent

    # Metrics
    st.metric("💸 Total Spent", f"₹ {total_spent}")
    st.metric("💰 Remaining Budget", f"₹ {remaining_after_spend}")

    # Budget alert
    if remaining_after_spend < 0:
        st.error("🚨 You have exceeded your budget!")
    elif remaining_after_spend < remaining_budget * 0.2:
        st.warning("⚠️ 80% budget used!")

    # Table
    st.dataframe(monthly_df.sort_values(by="date", ascending=False))

    # -------------------------------
    # 📊 CATEGORY CHART
    # -------------------------------
    st.subheader("📊 Category Breakdown")
    cat_data = monthly_df.groupby("category")["amount"].sum()
    st.bar_chart(cat_data)

    # -------------------------------
    # 💳 PAYMENT MODE CHART
    # -------------------------------
    st.subheader("💳 Payment Mode Usage")
    pay_data = monthly_df.groupby("payment_mode")["amount"].sum()
    st.bar_chart(pay_data)

    # -------------------------------
    # 📈 DAILY TREND
    # -------------------------------
    st.subheader("📈 Daily Spending Trend")
    daily_data = monthly_df.groupby("date")["amount"].sum()
    st.line_chart(daily_data)

else:
    st.info("No expenses yet — start adding!")
