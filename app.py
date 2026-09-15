import sqlite3
from datetime import date

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

DATABASE = "applications.db"


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
    with get_database_connection() as connection:
        applications = connection.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        ).fetchall()

    interviews = sum(app["status"] == "Interview" for app in applications)
    offers = sum(app["status"] == "Offer" for app in applications)

    return render_template(
        "index.html",
        applications=applications,
        total=len(applications),
        interviews=interviews,
        offers=offers,
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