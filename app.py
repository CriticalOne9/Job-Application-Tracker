import os
from functools import wraps
from dotenv import load_dotenv
import sqlite3
import psycopg
from psycopg import errors
from psycopg.rows import dict_row
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
DATABASE_URL = os.getenv("DATABASE_URL")
SQL_PLACEHOLDER = "%s" if DATABASE_URL else "?"
ALLOWED_STATUSES = ("Applied", "Interview", "Offer", "Rejected")


def get_database_connection():
    if DATABASE_URL:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("landing"))

        return view(*args, **kwargs)

    return wrapped_view

def initialize_database():
    with get_database_connection() as connection:
        if DATABASE_URL:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    company TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    date_applied TEXT NOT NULL,
                    user_id INTEGER
                )
                """
            )
        else:
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

        if DATABASE_URL:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        else:
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

        if not DATABASE_URL:
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
    conditions = [f"user_id = {SQL_PLACEHOLDER}"]
    parameters = [session["user_id"]]

    if search:
        conditions.append(
            f"(company LIKE {SQL_PLACEHOLDER} OR role LIKE {SQL_PLACEHOLDER})"
        )
        parameters.extend([f"%{search}%", f"%{search}%"])

    if selected_status in ALLOWED_STATUSES:
        conditions.append(f"status = {SQL_PLACEHOLDER}")
        parameters.append(selected_status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    with get_database_connection() as connection:
        applications = connection.execute(query, parameters).fetchall()
        total = connection.execute(
            f"SELECT COUNT(*) AS count FROM applications WHERE user_id = {SQL_PLACEHOLDER}",
            (session["user_id"],),
        ).fetchone()["count"]

        interviews = connection.execute(
            f"SELECT COUNT(*) AS count FROM applications WHERE status = 'Interview' AND user_id = {SQL_PLACEHOLDER}",
            (session["user_id"],),
        ).fetchone()["count"]

        offers = connection.execute(
            f"SELECT COUNT(*) AS count FROM applications WHERE status = 'Offer' AND user_id = {SQL_PLACEHOLDER}",
            (session["user_id"],),
        ).fetchone()["count"]

        status_counts = {}

        for status in ALLOWED_STATUSES:
            status_counts[status] = connection.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM applications
                WHERE status = {SQL_PLACEHOLDER}
                AND user_id = {SQL_PLACEHOLDER}
                """,
                (status, session["user_id"]),
            ).fetchone()["count"]

        applications_over_time = {}

        rows = connection.execute(
            f"""
            SELECT date_applied, COUNT(*) AS count
            FROM applications
            WHERE user_id = {SQL_PLACEHOLDER}
            GROUP BY date_applied
            ORDER BY date_applied
            """,
            (session["user_id"],),
        ).fetchall()

        for row in rows:
            applications_over_time[row["date_applied"]] = row["count"]

        if applications_over_time:
            start_date = date.fromisoformat(min(applications_over_time))
            end_date = date.fromisoformat(max(applications_over_time))

            current_date = start_date

            while current_date <= end_date:
                date_key = current_date.isoformat()

                if date_key not in applications_over_time:
                    applications_over_time[date_key] = 0

                current_date += timedelta(days=1)

            applications_over_time = dict(sorted(applications_over_time.items()))
    return render_template(
        "dashboard.html",
        applications=applications,
        total=total,
        interviews=interviews,
        offers=offers,
        search=search,
        selected_status=selected_status,
        statuses=ALLOWED_STATUSES,
        status_counts=status_counts,
        applications_over_time=applications_over_time,
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
            f"""
            INSERT INTO applications (
                company,
                role,
                status,
                date_applied,
                user_id
            )
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
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
                f"UPDATE applications SET status = {SQL_PLACEHOLDER} WHERE id = {SQL_PLACEHOLDER} AND user_id = {SQL_PLACEHOLDER}",
                (status, application_id, session["user_id"]),
            )

    return redirect(url_for("home"))

@app.post("/applications/<int:application_id>/delete")
@login_required
def delete_application(application_id):
    with get_database_connection() as connection:
        connection.execute(
            f"DELETE FROM applications WHERE id = {SQL_PLACEHOLDER} AND user_id = {SQL_PLACEHOLDER}",
            (application_id, session["user_id"]),
        )

    return redirect(url_for("home"))

@app.post("/register")
def register():
    username = request.form["username"].strip()
    password = request.form["password"]

    if not username:
        return jsonify({
            "success": False,
            "error": "Please enter a username."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "error": "Your password must have at least 8 characters."
        }), 400

    try:
        with get_database_connection() as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO users (username, password_hash, created_at)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                RETURNING id
                """,
                (
                    username,
                    generate_password_hash(password),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            user_id = cursor.fetchone()["id"]
    except (sqlite3.IntegrityError, errors.UniqueViolation):
        return jsonify({
            "success": False,
            "error": "An account with that username already exists."
        }), 400

    session.clear()
    session["user_id"] = user_id

    return jsonify({
        "success": True,
        "redirect": url_for("home")
    })

@app.post("/login")
def login():
    username = request.form["username"].strip()
    password = request.form["password"]

    with get_database_connection() as connection:
        user = connection.execute(
            f"SELECT * FROM users WHERE username = {SQL_PLACEHOLDER}",
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
    return redirect(url_for("landing"))

initialize_database()
if __name__ == "__main__":
    app.run(debug=True)