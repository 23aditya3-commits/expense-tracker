import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# Page config (mobile friendly)
st.set_page_config(page_title="Expense Tracker", layout="centered")

# DB setup
conn = sqlite3.connect("expenses.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL,
    category TEXT,
    date TEXT,
    note TEXT
)
""")
conn.commit()

st.title("💰 Expense Tracker")

# --- QUICK ADD BUTTONS (1-tap logging) ---
st.subheader("⚡ Quick Add")

col1, col2, col3 = st.columns(3)

if col1.button("₹100 Food"):
    c.execute("INSERT INTO expenses (amount, category, date, note) VALUES (?,?,?,?)",
              (100, "Food", str(date.today()), "Quick"))
    conn.commit()
    st.success("Added ₹100 Food")

if col2.button("₹200 Travel"):
    c.execute("INSERT INTO expenses (amount, category, date, note) VALUES (?,?,?,?)",
              (200, "Travel", str(date.today()), "Quick"))
    conn.commit()
    st.success("Added ₹200 Travel")

if col3.button("₹500 Other"):
    c.execute("INSERT INTO expenses (amount, category, date, note) VALUES (?,?,?,?)",
              (500, "Other", str(date.today()), "Quick"))
    conn.commit()
    st.success("Added ₹500 Other")

st.divider()

# --- MANUAL ADD ---
st.subheader("➕ Add Expense")

amount = st.number_input("Amount", step=10)
category = st.selectbox("Category", ["Food", "Travel", "Rent", "Other"])
exp_date = st.date_input("Date", date.today())
note = st.text_input("Note")

if st.button("Add Expense"):
    c.execute("INSERT INTO expenses (amount, category, date, note) VALUES (?, ?, ?, ?)",
              (amount, category, str(exp_date), note))
    conn.commit()
    st.success("Expense added!")

st.divider()

# --- VIEW ---
st.subheader("📊 Summary")

df = pd.read_sql("SELECT * FROM expenses", conn)

if not df.empty:
    st.write("Total Spent:", df['amount'].sum())
    st.dataframe(df[::-1])  # latest first
else:
    st.info("No expenses yet")