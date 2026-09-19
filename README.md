# Job Application Tracker

A full-stack web application for organizing job applications and tracking the progress of a job search.

## Features

- User registration and login through the landing page
- Secure password hashing
- Session-based authentication with 1-hour session expiration
- CSRF protection for state-changing requests
- User-specific application data isolation
- Add applications with company, role, and status
- Search and filter applications
- Update application status
- Delete applications
- Dashboard statistics for total applications, interviews, and offers
- SQLite support for local development
- PostgreSQL support for production deployment

## Tech Stack

### Backend

- Python
- Flask
- SQLite for local development
- PostgreSQL for production
- psycopg
- Flask-WTF (CSRF protection)
- Werkzeug password hashing

### Frontend

- HTML
- CSS
- JavaScript
- Jinja templates

### Deployment & Tools

- Gunicorn
- Render
- Supabase PostgreSQL
- python-dotenv
- Git & GitHub

## Project Structure

```text
Job-Application-Tracker/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── landing.html
│   └── dashboard.html
└── static/
    ├── styles.css
    └── background.jpg
```

## Running Locally

### 1. Clone the repository

```bash
git clone <repository-url>
cd Job-Application-Tracker
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-secret-key
```

For local development, the application uses SQLite automatically when `DATABASE_URL` is not set.

If you want to run against PostgreSQL locally, also provide:

```env
DATABASE_URL=your-postgresql-connection-string
```

### 5. Start the application

```bash
python app.py
```

Then open the local address shown by Flask in your browser.

## Database Behavior

The application supports two database environments:

- **Local development:** SQLite (`applications.db`)
- **Production:** PostgreSQL, configured through `DATABASE_URL`

The application creates the required `users` and `applications` tables when it starts if they do not already exist.

## Deployment

The application is configured for deployment on Render using Gunicorn. In production, `DATABASE_URL` points to a PostgreSQL database hosted by Supabase.

The production server can be started with:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Environment variables such as `FLASK_SECRET_KEY` and `DATABASE_URL` should be configured in the hosting provider rather than committed to the repository.

## Authentication & Security

- Passwords are stored as hashes rather than plaintext passwords.
- Flask sessions are used to maintain authentication state.
- Sessions are configured to expire after one hour.
- CSRF tokens protect state-changing form submissions.
- Application queries are restricted by the authenticated user's ID so users only access their own applications.
- Secrets and database credentials are provided through environment variables.
