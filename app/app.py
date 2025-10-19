# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import mysql.connector
from mysql.connector import pooling
from passlib.hash import bcrypt
import secrets

# 環境変数
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "myapp")
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(16))

app = Flask(__name__)
app.secret_key = SECRET_KEY

# コネクションプール
cnxpool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    auth_plugin='mysql_native_password'
)

def get_conn():
    return cnxpool.get_connection()

# ---- ユーティリティ ----
def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

# CSRF簡易トークン
def generate_csrf():
    token = secrets.token_hex(16)
    session['csrf_token'] = token
    return token

def check_csrf(token):
    return token and session.get('csrf_token') == token

# ---- ルート ----
@app.route("/")
def index():
    user = None
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
    return render_template("index.html", user=user)

# 登録ページ
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("ユーザー名とパスワードを入力してください。")
            return redirect(url_for("register"))

        # ユーザー名既存チェック
        if get_user_by_username(username):
            flash("そのユーザー名は既に使われています。")
            return redirect(url_for("register"))

        password_hash = bcrypt.hash(password)

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            conn.commit()
            flash("登録が完了しました。ログインしてください。")
            return redirect(url_for("login"))
        except mysql.connector.Error as e:
            conn.rollback()
            flash("登録に失敗しました。")
            return redirect(url_for("register"))
        finally:
            cur.close()
            conn.close()

    # GET
    return render_template("register.html")

# ログイン
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if not user:
            flash("ユーザー名かパスワードが違います。")
            return redirect(url_for("login"))
        if bcrypt.verify(password, user["password_hash"]):
            session.clear()
            session["user_id"] = user["id"]
            generate_csrf()
            flash("ログインしました。")
            return redirect(url_for("account"))
        else:
            flash("ユーザー名かパスワードが違います。")
            return redirect(url_for("login"))

    return render_template("login.html")

# ログアウト
@app.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。")
    return redirect(url_for("login"))

# マイページ（アカウント操作）
@app.route("/account", methods=["GET"])
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    csrf = generate_csrf()
    return render_template("account.html", user=user, csrf=csrf)

# アカウント削除（POSTのみ）
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        abort(403)
    token = request.form.get("csrf_token")
    if not check_csrf(token):
        abort(400, "CSRF token invalid")
    user_id = session["user_id"]

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
    except mysql.connector.Error:
        conn.rollback()
        flash("アカウント削除に失敗しました。")
        return redirect(url_for("account"))
    finally:
        cur.close()
        conn.close()

    session.clear()
    flash("アカウントを削除しました。")
    return redirect(url_for("register"))

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
