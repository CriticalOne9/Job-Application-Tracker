#Job Application Tracker----

A full-stack web application for organizing job applications and tracking their progress.

#Features------

- User registration and login
- Secure password hashing
- Session-based authentication
- Automatic session expiration after 1 hour
- CSRF protection for state-changing requests
- User-specific application data isolation
- Add applications with company name, job title, and status
- View all saved applications in a dashboard
- Search and filter applications
- Update an application's status
- Delete applications
- Track total applications, interviews, and offers
- Persist data locally with SQLite

#Tech Stack-------

- Python
- Flask
- Flask-WTF
- SQLite
- HTML and CSS
- Git and GitHub

#How to run locally------

1. Clone this repository.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1