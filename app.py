# ==============================
# 📌 Rent Manager Flask App
# ==============================

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DATABASE = "rent_manager.db"


# ==============================
# 📌 Database Setup
# ==============================

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_name TEXT,
        payment_date TEXT,
        amount REAL,
        from_date TEXT,
        to_date TEXT,
        receipt_filename TEXT,
        submitted_at TEXT
    )
""")
    conn.commit()
    conn.close()

init_db()


# ==============================
# 📌 Home - Submit Form
# ==============================

@app.route("/", methods=["GET", "POST"])
def submit():
    if request.method == "POST":

        tenant_name = request.form["tenant_name"]
        payment_date = request.form["payment_date"]
        amount = request.form["amount"]
        from_date = request.form["from_date"]
        to_date = request.form["to_date"]
        file = request.files["receipt"]
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
    INSERT INTO payments 
    (tenant_name, payment_date, amount, from_date, to_date, receipt_filename, submitted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    tenant_name,
    payment_date,
    amount,
    from_date,
    to_date,
    filename,
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
))
        conn.commit()
        conn.close()

        flash("Payment submitted successfully!", "success")
        return redirect(url_for("submit"))

    return render_template("submit.html")


# ==============================
# 📌 Admin Login
# ==============================

@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        password = request.form["password"]

        if password == "admin123":
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid password", "danger")

    return render_template("admin_login.html")


# ==============================
# 📌 Dashboard
# ==============================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row   
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments ORDER BY payment_date DESC")
    payments = cursor.fetchall()
    conn.close()

    return render_template("dashboard.html", payments=payments)

# ==============================
# 📌 Logout
# ==============================

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("submit"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)