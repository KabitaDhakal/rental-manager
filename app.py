# ==============================
# 📌 Rent Manager Flask App
# ==============================

from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = "supersecretkey"

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
        category TEXT,
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
# 📌 Submit Payment
# ==============================

@app.route("/", methods=["GET", "POST"])
def submit():

    if request.method == "POST":

        tenant_name = request.form["tenant_name"]
        category = request.form["category"]
        payment_date = request.form["payment_date"]
        amount = request.form["amount"]
        from_date = request.form["from_date"]
        to_date = request.form["to_date"]

        # ✅ FIXED HERE
        file = request.files.get("receipt")
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO payments
        (category, tenant_name, payment_date, amount, from_date, to_date, receipt_filename, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
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
        if request.form["password"] == "admin123":
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

    # Payments
    cursor.execute("SELECT * FROM payments WHERE category='rent' ORDER BY submitted_at DESC")
    rent_payments = cursor.fetchall()

    cursor.execute("SELECT * FROM payments WHERE category='electricity_gas'")
    electricity_payments = cursor.fetchall()

    cursor.execute("SELECT * FROM payments WHERE category='internet'")
    internet_payments = cursor.fetchall()

    # Cycle
    cycle_start = "2026-03-21"
    cycle_end = "2026-04-03"

    # Tenants (they pay YOU)
    tenant_rent = {
        "Tenant1": 600,
        "Tenant2": 600
    }

    tenant_status = []

    for tenant, expected in tenant_rent.items():

        cursor.execute("""
        SELECT SUM(amount) as total
        FROM payments
        WHERE tenant_name=? AND category='rent' AND from_date=?
        """, (tenant, cycle_start))

        result = cursor.fetchone()
        paid = result["total"] if result["total"] else 0

        if paid >= expected:
            status = "Paid"
        elif paid > 0:
            status = "Partial"
        else:
            status = "Unpaid"

        tenant_status.append({
            "name": tenant,
            "paid": paid,
            "expected": expected,
            "status": status
        })

    # Kabita → Owner
    cursor.execute("""
    SELECT SUM(amount) as total
    FROM payments
    WHERE tenant_name='Kabita' AND category='rent' AND from_date=?
    """, (cycle_start,))

    result = cursor.fetchone()
    your_paid = result["total"] if result["total"] else 0

    owner_rent = 1900

    if your_paid >= owner_rent:
        your_status = "Paid"
    elif your_paid > 0:
        your_status = "Partial"
    else:
        your_status = "Unpaid"

    your_remaining = owner_rent - your_paid

    conn.close()

    return render_template(
        "dashboard.html",
        rent_payments=rent_payments,
        electricity_payments=electricity_payments,
        internet_payments=internet_payments,
        tenant_status=tenant_status,
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        your_paid=your_paid,
        your_status=your_status,
        owner_rent=owner_rent,
        your_remaining=your_remaining
    )


# ==============================
# Delete
# ==============================

@app.route("/delete/<int:id>")
def delete_payment(id):

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM payments WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ==============================
# CSV Download
# ==============================

@app.route("/download")
def download():

    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM payments")
    rows = cursor.fetchall()
    conn.close()

    def generate():
        yield "Category,Tenant,Amount,Payment Date,From,To,Receipt,Submitted\n"
        for r in rows:
            yield f"{r['category']},{r['tenant_name']},{r['amount']},{r['payment_date']},{r['from_date']},{r['to_date']},{r['receipt_filename']},{r['submitted_at']}\n"

    return Response(generate(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=payments.csv"})


# ==============================
# Logout
# ==============================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("submit"))


# ==============================
# Run
# ==============================

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)