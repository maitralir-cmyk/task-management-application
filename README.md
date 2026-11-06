# TaskFlow – Task Management Application

A responsive full-stack task manager built with **Python, Flask, SQLite, HTML, CSS and JavaScript**.

## Features

- User registration and login with securely hashed passwords
- Session-based authentication
- Each user can access and manage only their own tasks
- Create, read, update and delete (CRUD) tasks
- Task due dates, priority levels and status
- Automatic overdue highlighting
- Dashboard summary: total, completed, in progress and overdue
- Search tasks by title or description
- Filter by status and priority
- Responsive layout for desktop and mobile
- JSON REST API for task operations

## Requirements

- Python 3.9 or newer
- VS Code (recommended)
- Internet connection only for the Google Fonts stylesheet; the app itself runs locally

## Run in VS Code

1. Extract `task_management_application.zip`.
2. Open the extracted `task_management_application` folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   **Windows**
   ```bash
   py -m venv venv
   venv\\Scripts\\activate
   ```

   **macOS / Linux**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the application:
   ```bash
   python app.py
   ```
7. Open this address in your browser:
   `http://127.0.0.1:5000`
8. Register a new account and start creating tasks.

The SQLite database file `tasks.db` is created automatically on first run.

## REST API

All API endpoints require a logged-in session. JSON responses are returned.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tasks` | List your tasks |
| POST | `/api/tasks` | Create a task |
| GET | `/api/tasks/<id>` | Get one of your tasks |
| PUT | `/api/tasks/<id>` | Update one of your tasks |
| DELETE | `/api/tasks/<id>` | Delete one of your tasks |

Example JSON for `POST /api/tasks`:

```json
{
  "title": "Prepare project presentation",
  "description": "Complete slides and practice the demo.",
  "due_date": "2026-11-20",
  "priority": "High",
  "status": "Pending"
}
```

Allowed priority values: `Low`, `Medium`, `High`.

Allowed status values: `Pending`, `In Progress`, `Completed`.

## Project structure

```text
task_management_application/
│
├── app.py
├── requirements.txt
├── README.md
├── tasks.db              # created automatically when app runs
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── task_form.html
│
└── static/
    ├── style.css
    └── app.js
```

## Important security note

This is a student/local-development project. Before deploying publicly:
- Set a long, random `SECRET_KEY` environment variable.
- Run with `debug=False` behind a production WSGI server.
- Add CSRF protection and HTTPS.
- Configure database backups and production-grade hosting.

## Scope note

The screenshot describes real-time WebSocket updates as optional. This version provides a working task manager with normal request/response updates and a REST API; WebSocket live synchronization is not included.
