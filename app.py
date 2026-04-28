import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Page config
st.set_page_config(page_title="Expense Tracker", layout="centered")

# DB setup
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()

# UPDATED TABLE (added payment_mode)
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
conn.commit()

st.title("💰 Expense Tracker")

# =========================
# 💰 MONTHLY BUDGET SECTION
# =========================
st.subheader("💰 Monthly Budget Planner")

income = st.number_input("Monthly Income", min_value=0)
investments = st.number_input("Investments", min_value=0)
sent_home = st.number_input("Sent to Home", min_value=0)
emi = st.number_input("EMI", min_value=0)

remaining_budget = income - (investments + sent_home + emi)

st.success(f"💸 Remaining Budget for Expenses: ₹ {remaining_budget}")

st.divider()

# =========================
# 🧾 EXPENSE ENTRY SECTION
# =========================
st.subheader("🧾 Add Expense")

# Date (default today)
exp_date = st.date_input("Date", date.today())

# Payment Mode
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

# Category
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

# Amount
amount = st.number_input("Amount", min_value=0)

# Notes
note = st.text_input("Note")

# Save Button
if st.button("Add Expense"):
    c.execute(
        "INSERT INTO expenses (amount, category, payment_mode, date, note) VALUES (?, ?, ?, ?, ?)",
        (amount, category, payment_mode, str(exp_date), note)
    )
    conn.commit()
    st.success("✅ Expense Added!")

st.divider()

# =========================
# 📊 SUMMARY SECTION
# =========================
st.subheader("📊 Summary")

df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    total_spent = df['amount'].sum()

    st.metric("💸 Total Spent", f"₹ {total_spent}")
    st.metric("💰 Remaining Budget", f"₹ {remaining_budget - total_spent}")

    st.dataframe(df[::-1])  # latest first
else:
    st.info("No expenses yet")
