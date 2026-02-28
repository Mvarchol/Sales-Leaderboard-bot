from flask import Flask, request
import requests
import sqlite3

app = Flask(__name__)

BOT_ID = "0d2777747c529b89f75d0e3194"

ADMINS = ["Matthew Varchol" , "Nick Scordos" , "Amanda Rickman"]

# ---------------------
# DATABASE SETUP
# ---------------------

def init_db():
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            name TEXT PRIMARY KEY,
            weekly_total INTEGER DEFAULT 0,
            monthly_total INTEGER DEFAULT 0,
            emoji TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def update_sales(name, amount):
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("SELECT weekly_total, monthly_total FROM sales WHERE name = ?", (name,))
    row = c.fetchone()

    if row:
        new_weekly = row[0] + amount
        new_monthly = row[1] + amount
        c.execute("""
            UPDATE sales
            SET weekly_total = ?, monthly_total = ?
            WHERE name = ?
        """, (new_weekly, new_monthly, name))
    else:
        c.execute("""
            INSERT INTO sales (name, weekly_total, monthly_total)
            VALUES (?, ?, ?)
        """, (name, amount, amount))

    conn.commit()
    conn.close()

def set_emoji(name, emoji):
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()

    c.execute("SELECT name FROM sales WHERE name = ?", (name,))
    if not c.fetchone():
        c.execute("INSERT INTO sales (name) VALUES (?)", (name,))

    c.execute("UPDATE sales SET emoji = ? WHERE name = ?", (emoji, name))
    conn.commit()
    conn.close()

def get_leaderboard(period="weekly"):
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()

    if period == "weekly":
        c.execute("SELECT name, weekly_total, emoji FROM sales ORDER BY weekly_total DESC")
    else:
        c.execute("SELECT name, monthly_total, emoji FROM sales ORDER BY monthly_total DESC")

    rows = c.fetchall()
    conn.close()
    return rows

def milestone_label(total):
    if total >= 30000:
        return "💎 30K Club"
    elif total >= 20000:
        return "🥇 20K Club"
    elif total >= 10000:
        return "🚀 10K Club"
    elif total >= 5000:
        return "🎯 5K Club"
    elif total >= 4000:
        return "⭐ 4K Starter"
    else:
        return ""

def post_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})

# ---------------------
# WEBHOOK
# ---------------------

@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    name = data["name"]
    text = data["text"]

    # -------- SET EMOJI --------
    if text.lower().startswith("!setemoji"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            post_message("Usage: !setemoji 😎")
            return "ok", 200

        emoji = parts[1].strip()
        set_emoji(name, emoji)
        post_message(f"{name} set their leaderboard emoji to {emoji}")
        return "ok", 200

    # -------- SALES ENTRY --------
    if text.startswith("+") and text[1:].isdigit():
        amount = int(text[1:])
        update_sales(name, amount)

        leaderboard = get_leaderboard("weekly")

        message = "🏆 Weekly Sales Leaderboard\n\n"
        for i, (n, t, e) in enumerate(leaderboard, 1):
            emoji_display = f"{e} " if e else ""
            message += f"{i}. {emoji_display}{n} – ${t:,} {milestone_label(t)}\n"

        post_message(message)
        return "ok", 200

    # -------- MY TOTAL --------
    if text.lower() == "!mytotal":
        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("SELECT weekly_total, monthly_total FROM sales WHERE name = ?", (name,))
        row = c.fetchone()
        conn.close()

        if row:
            post_message(
                f"📊 {name}'s Totals\n\n"
                f"Weekly: ${row[0]:,}\n"
                f"Monthly: ${row[1]:,}"
            )
        else:
            post_message(f"{name}, you have no recorded sales yet.")

        return "ok", 200

    # -------- RESET WEEKLY --------
    if text.lower() == "!resetweekly":
        if name not in ADMINS:
            post_message("⛔ Unauthorized.")
            return "ok", 200

        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("UPDATE sales SET weekly_total = 0")
        conn.commit()
        conn.close()

        post_message("📅 Weekly totals reset by admin.")
        return "ok", 200

    # -------- RESET MONTHLY --------
    if text.lower() == "!resetmonthly":
        if name not in ADMINS:
            post_message("⛔ Unauthorized.")
            return "ok", 200

        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("UPDATE sales SET monthly_total = 0")
        conn.commit()
        conn.close()

        post_message("🗓 Monthly totals reset by admin.")
        return "ok", 200

    return "ok", 200

import os

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)