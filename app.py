import os
from functools import wraps
from dotenv import load_dotenv
import sqlite3
from datetime import date,datetime,timedelta
from flask import Flask, redirect, render_template, request, session, url_for,jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
csrf = CSRFProtect(app)

DATABASE = "applications.db"
ALLOWED_STATUSES = ("Applied", "Interview", "Offer", "Rejected")


def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login_page"))

        return view(*args, **kwargs)

    return wrapped_view

def initialize_database():
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                date_applied TEXT NOT NULL,
                user_id INTEGER
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        application_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(applications)"
            ).fetchall()
        }

        if "user_id" not in application_columns:
            connection.execute(
                "ALTER TABLE applications ADD COLUMN user_id INTEGER"
            )

@app.get("/")
def landing():
    return render_template("landing.html")

@app.route("/dashboard")
@login_required
def home():
    search = request.args.get("search", "").strip()
    selected_status = request.args.get("status", "All")

    query = "SELECT * FROM applications"
    conditions = ["user_id = ?"]
    parameters = [session["user_id"]]

    if search:
        conditions.append("(company LIKE ? OR role LIKE ?)")
        parameters.extend([f"%{search}%", f"%{search}%"])

    if selected_status in ALLOWED_STATUSES:
        conditions.append("status = ?")
        parameters.append(selected_status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    with get_database_connection() as connection:
        applications = connection.execute(query, parameters).fetchall()
        total = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE user_id = ?",
            (session["user_id"],),
        ).fetchone()[0]
        interviews = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Interview' AND user_id = ?",
            (session["user_id"],),
        ).fetchone()[0]
        offers = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Offer' AND user_id = ?",
        (session["user_id"],),
        ).fetchone()[0]

    return render_template(
        "dashboard.html",
        applications=applications,
        total=total,
        interviews=interviews,
        offers=offers,
        search=search,
        selected_status=selected_status,
        statuses=ALLOWED_STATUSES,
    )


@app.post("/applications")
@login_required
def add_application():
    company = request.form["company"].strip()
    role = request.form["role"].strip()
    if not company or not role:
        return redirect(url_for("home"))
    status = request.form["status"]
    if status not in ALLOWED_STATUSES:
        return redirect(url_for("home"))

    with get_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO applications (
                company,
                role,
                status,
                date_applied,
                user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                company,
                role,
                status,
                date.today().isoformat(),
                session["user_id"],
            ),
        )

    return redirect(url_for("home"))

@app.post("/applications/<int:application_id>/status")
@login_required
def update_status(application_id):
    status = request.form["status"]

    if status in ALLOWED_STATUSES:
        with get_database_connection() as connection:
            connection.execute(
                "UPDATE applications SET status = ? WHERE id = ? AND user_id = ?",
                (status, application_id, session["user_id"]),
            )

    return redirect(url_for("home"))

@app.post("/applications/<int:application_id>/delete")
@login_required
def delete_application(application_id):
    with get_database_connection() as connection:
        connection.execute(
            "DELETE FROM applications WHERE id = ? AND user_id = ?",
            (application_id, session["user_id"]),
        )

    return redirect(url_for("home"))

@app.get("/register")
def register_page():
    return render_template("register.html")


@app.post("/register")
def register():
    username = request.form["username"].strip()
    password = request.form["password"]

    if not username:
        return render_template(
            "register.html",
            error="Please enter a username.",
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Your password must have at least 8 characters.",
        )

    try:
        with get_database_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    generate_password_hash(password),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that username already exists.",
        )

    session.clear()
    session["user_id"] = cursor.lastrowid

    return redirect(url_for("home"))

@app.get("/login")
def login_page():
    return render_template("login.html")


@app.post("/login")
def login():
    username = request.form["username"].strip()
    password = request.form["password"]

    with get_database_connection() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": False,
                "error": "Invalid username or password."
            }), 401

        return render_template(
                "landing.html",
                login_error="Invalid username or password.",
            )

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
        "success": True,
        "redirect": url_for("home")
    })

    return redirect(url_for("home"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)