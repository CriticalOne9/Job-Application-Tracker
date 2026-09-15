import sqlite3
from datetime import date

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

DATABASE = "applications.db"
ALLOWED_STATUSES = ("Applied", "Interview", "Offer", "Rejected")


def get_database_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                date_applied TEXT NOT NULL
            )
            """
        )


@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    selected_status = request.args.get("status", "All")

    query = "SELECT * FROM applications"
    conditions = []
    parameters = []

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
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0]
        interviews = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Interview'"
        ).fetchone()[0]
        offers = connection.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Offer'"
        ).fetchone()[0]

    return render_template(
        "index.html",
        applications=applications,
        total=total,
        interviews=interviews,
        offers=offers,
        search=search,
        selected_status=selected_status,
        statuses=ALLOWED_STATUSES,
    )


@app.post("/applications")
def add_application():
    company = request.form["company"].strip()
    role = request.form["role"].strip()
    status = request.form["status"]

    with get_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO applications (company, role, status, date_applied)
            VALUES (?, ?, ?, ?)
            """,
            (company, role, status, date.today().isoformat()),
        )

    return redirect(url_for("home"))

@app.post("/applications/<int:application_id>/status")
def update_status(application_id):
    status = request.form["status"]

    if status in ALLOWED_STATUSES:
        with get_database_connection() as connection:
            connection.execute(
                "UPDATE applications SET status = ? WHERE id = ?",
                (status, application_id),
            )

    return redirect(url_for("home"))

@app.post("/applications/<int:application_id>/delete")
def delete_application(application_id):
    with get_database_connection() as connection:
        connection.execute(
            "DELETE FROM applications WHERE id = ?",
            (application_id,),
        )

    return redirect(url_for("home"))


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)