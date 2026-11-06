import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
DB_PATH = os.path.join(os.path.dirname(__file__), "tasks.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            due_date TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please log in."}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def task_for_user(task_id):
    with get_db() as db:
        task = db.execute("SELECT * FROM tasks WHERE id=? AND user_id=?",
                          (task_id, session["user_id"])).fetchone()
    if task is None:
        abort(404)
    return task

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name"), "today": date.today().isoformat()}

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Please complete all required fields.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            try:
                with get_db() as db:
                    db.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                               (name, email, generate_password_hash(password)))
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("An account with this email already exists.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    query = "SELECT * FROM tasks WHERE user_id=?"
    params = [session["user_id"]]
    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if status in ("Pending", "In Progress", "Completed"):
        query += " AND status=?"
        params.append(status)
    if priority in ("Low", "Medium", "High"):
        query += " AND priority=?"
        params.append(priority)
    query += """ ORDER BY CASE status WHEN 'Pending' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END,
                 CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
                 due_date IS NULL, due_date ASC, created_at DESC"""
    with get_db() as db:
        tasks = db.execute(query, params).fetchall()
        all_tasks = db.execute("SELECT * FROM tasks WHERE user_id=?", (session["user_id"],)).fetchall()
    total = len(all_tasks)
    completed = sum(t["status"] == "Completed" for t in all_tasks)
    in_progress = sum(t["status"] == "In Progress" for t in all_tasks)
    pending = sum(t["status"] == "Pending" for t in all_tasks)
    overdue = sum(t["status"] != "Completed" and t["due_date"] and t["due_date"] < date.today().isoformat() for t in all_tasks)
    return render_template("dashboard.html", tasks=tasks, stats={
        "total": total, "completed": completed, "in_progress": in_progress,
        "pending": pending, "overdue": overdue
    }, filters={"q": search, "status": status, "priority": priority})

@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date") or None
        priority = request.form.get("priority", "Medium")
        status = request.form.get("status", "Pending")
        if not title:
            flash("Task title is required.", "error")
        elif priority not in ("Low", "Medium", "High") or status not in ("Pending", "In Progress", "Completed"):
            flash("Invalid task priority or status.", "error")
        else:
            with get_db() as db:
                db.execute("""INSERT INTO tasks(user_id,title,description,due_date,priority,status)
                              VALUES(?,?,?,?,?,?)""",
                           (session["user_id"], title, description, due_date, priority, status))
            flash("Task created successfully.", "success")
            return redirect(url_for("dashboard"))
    return render_template("task_form.html", task=None, heading="Create a task")

@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = task_for_user(task_id)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date") or None
        priority = request.form.get("priority", "Medium")
        status = request.form.get("status", "Pending")
        if not title:
            flash("Task title is required.", "error")
        elif priority not in ("Low", "Medium", "High") or status not in ("Pending", "In Progress", "Completed"):
            flash("Invalid task priority or status.", "error")
        else:
            with get_db() as db:
                db.execute("""UPDATE tasks SET title=?,description=?,due_date=?,priority=?,status=?,
                              updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?""",
                           (title, description, due_date, priority, status, task_id, session["user_id"]))
            flash("Task updated successfully.", "success")
            return redirect(url_for("dashboard"))
    return render_template("task_form.html", task=task, heading="Edit task")

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task_for_user(task_id)
    with get_db() as db:
        db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session["user_id"]))
    flash("Task deleted.", "success")
    return redirect(url_for("dashboard"))

@app.route("/api/tasks", methods=["GET", "POST"])
@login_required
def api_tasks():
    if request.method == "GET":
        with get_db() as db:
            rows = db.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY created_at DESC",
                              (session["user_id"],)).fetchall()
        return jsonify([dict(row) for row in rows])
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    priority = data.get("priority", "Medium")
    status = data.get("status", "Pending")
    if priority not in ("Low", "Medium", "High") or status not in ("Pending", "In Progress", "Completed"):
        return jsonify({"error": "Invalid priority or status."}), 400
    with get_db() as db:
        cur = db.execute("""INSERT INTO tasks(user_id,title,description,due_date,priority,status)
                            VALUES(?,?,?,?,?,?)""",
                         (session["user_id"], title, data.get("description", ""),
                          data.get("due_date") or None, priority, status))
        task_id = cur.lastrowid
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return jsonify(dict(row)), 201

@app.route("/api/tasks/<int:task_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_task_detail(task_id):
    task_for_user(task_id)
    if request.method == "GET":
        return jsonify(dict(task_for_user(task_id)))
    if request.method == "DELETE":
        with get_db() as db:
            db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session["user_id"]))
        return jsonify({"message": "Task deleted."})
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    priority = data.get("priority", "Medium")
    status = data.get("status", "Pending")
    if not title:
        return jsonify({"error": "Title is required."}), 400
    if priority not in ("Low", "Medium", "High") or status not in ("Pending", "In Progress", "Completed"):
        return jsonify({"error": "Invalid priority or status."}), 400
    with get_db() as db:
        db.execute("""UPDATE tasks SET title=?,description=?,due_date=?,priority=?,status=?,
                      updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?""",
                   (title, data.get("description", ""), data.get("due_date") or None,
                    priority, status, task_id, session["user_id"]))
    return jsonify(dict(task_for_user(task_id)))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
