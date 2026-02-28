from flask import Flask, request
import requests
import sqlite3
import os

app = Flask(__name__)

BOT_ID = "PASTE_YOUR_BOT_ID_HERE"
ADMINS = ["Matthew Varchol"]

# ---------------------
# DATABASE SETUP
# ---------------------

def init_db():
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            name TEXT PRIMARY KEY,
            weekly_sales INTEGER DEFAULT 0,
            monthly_sales INTEGER DEFAULT 0,
            weekly_leads INTEGER DEFAULT 0,
            monthly_leads INTEGER DEFAULT 0,
            emoji TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def update_stats(name, sale_amount, leads):
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("""
        SELECT weekly_sales, monthly_sales, weekly_leads, monthly_leads 
        FROM sales WHERE name = ?
    """, (name,))
    row = c.fetchone()

    if row:
        new_weekly_sales = row[0] + sale_amount
        new_monthly_sales = row[1] + sale_amount
        new_weekly_leads = row[2] + leads
        new_monthly_leads = row[3] + leads

        c.execute("""
            UPDATE sales
            SET weekly_sales = ?, monthly_sales = ?,
                weekly_leads = ?, monthly_leads = ?
            WHERE name = ?
        """, (new_weekly_sales, new_monthly_sales,
              new_weekly_leads, new_monthly_leads, name))
    else:
        c.execute("""
            INSERT INTO sales
            (name, weekly_sales, monthly_sales, weekly_leads, monthly_leads)
            VALUES (?, ?, ?, ?, ?)
        """, (name, sale_amount, sale_amount, leads, leads))

    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("""
        SELECT name, weekly_sales, weekly_leads, emoji
        FROM sales
        ORDER BY weekly_sales DESC
    """)
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

def set_emoji(name, emoji):
    conn = sqlite3.connect("sales.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO sales (name) VALUES (?)", (name,))
    c.execute("UPDATE sales SET emoji = ? WHERE name = ?", (emoji, name))
    conn.commit()
    conn.close()

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
        post_message(f"{name} set their emoji to {emoji}")
        return "ok", 200

    # -------- SALE + LEADS ENTRY --------
    # Format: +3000 6
    if text.startswith("+"):
        parts = text[1:].split()

        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            sale_amount = int(parts[0])
            leads = int(parts[1])

            update_stats(name, sale_amount, leads)

            leaderboard = get_leaderboard()

            message = "🏆 Weekly Sales Leaderboard\n\n"
            for i, (n, sales, leads_count, e) in enumerate(leaderboard, 1):
                emoji_display = f"{e} " if e else ""
                message += (
                    f"{i}. {emoji_display}{n} – "
                    f"${sales:,} | {leads_count} leads "
                    f"{milestone_label(sales)}\n"
                )

            post_message(message)
            return "ok", 200
        else:
            post_message("Format: +3000 6  (sale amount then leads)")
            return "ok", 200

    # -------- MY TOTAL --------
    if text.lower() == "!mytotal":
        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("""
            SELECT weekly_sales, monthly_sales,
                   weekly_leads, monthly_leads
            FROM sales WHERE name = ?
        """, (name,))
        row = c.fetchone()
        conn.close()

        if row:
            post_message(
                f"📊 {name}'s Totals\n\n"
                f"Weekly Sales: ${row[0]:,}\n"
                f"Weekly Leads: {row[2]}\n\n"
                f"Monthly Sales: ${row[1]:,}\n"
                f"Monthly Leads: {row[3]}"
            )
        else:
            post_message("No sales recorded yet.")

        return "ok", 200

    # -------- RESET WEEKLY --------
    if text.lower() == "!resetweekly":
        if name not in ADMINS:
            post_message("⛔ Unauthorized.")
            return "ok", 200

        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("""
            UPDATE sales
            SET weekly_sales = 0,
                weekly_leads = 0
        """)
        conn.commit()
        conn.close()

        post_message("📅 Weekly stats reset.")
        return "ok", 200

    # -------- RESET MONTHLY --------
    if text.lower() == "!resetmonthly":
        if name not in ADMINS:
            post_message("⛔ Unauthorized.")
            return "ok", 200

        conn = sqlite3.connect("sales.db")
        c = conn.cursor()
        c.execute("""
            UPDATE sales
            SET monthly_sales = 0,
                monthly_leads = 0
        """)
        conn.commit()
        conn.close()

        post_message("🗓 Monthly stats reset.")
        return "ok", 200

    return "ok", 200

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)