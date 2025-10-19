from flask import Flask, render_template, request, redirect, session
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "secret_key"  # セッション用キー

# --- DB 初期化 ---
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- パスワードハッシュ ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- 登録ページ ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]
        hashed = hash_password(password)

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, password) VALUES (?, ?)", (name, hashed))
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            return "このユーザー名は既に存在します。"
    return render_template("register.html")

# --- ログインページ ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]
        password = hash_password(request.form["password"])

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE name=? AND password=?", (name, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = name
            return redirect("/home")
        else:
            return "ユーザー名またはパスワードが間違っています。"
    return render_template("login.html")

# --- ホームページ ---
@app.route("/home")
def home():
    if "user" in session:
        return render_template("home.html", name=session["user"])
    return redirect("/login")

# --- アカウント削除 ---
@app.route("/delete", methods=["GET", "POST"])
def delete_account():
    if request.method == "POST":
        name = request.form["name"]
        password = hash_password(request.form["password"])

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE name=? AND password=?", (name, password))
        conn.commit()
        conn.close()

        return "アカウントを削除しました。"
    return render_template("delete.html")

# --- ログアウト ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
