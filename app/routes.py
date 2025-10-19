from flask import Blueprint, redirect, url_for, jsonify, render_template, flash, request, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3 

# ✅ Flask() は作らない
# app = Flask(__name__) ← これを削除
# ✅ 代わりに Blueprint のみを定義
main = Blueprint("main", __name__, template_folder="templates")

# ✅ users.db がない場合のみ作成
if not os.path.exists("users.db"):
    print("🗂 users.db が存在しないため作成します...")
    init_db()
else:
    print("✅ users.db は既に存在します")


@main.route('/')
def index():
    return render_template('index.html')


@main.route("/game")
def game():
    return render_template("game.html")


@main.route("/game1")
def game1():
    return render_template("game1.html")


@main.route("/kari")
def kari():
    return render_template("diary.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                      (username, generate_password_hash(password)))
            conn.commit()
            flash("登録が完了しました！ログインしてください。")
            return redirect(url_for("main.login"))
        except:
            flash("このユーザー名はすでに使われています。")
        finally:
            conn.close()
    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("ログイン成功！")
            return redirect(url_for("main.account"))
        else:
            flash("ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")


@main.route("/account")
def account():
    if "username" not in session:
        return redirect(url_for("main.login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    user = c.fetchone()
    conn.close()

    return render_template("account.html", user=user)


@main.route("/account/update", methods=["POST"])
def update_account():
    username = session.get("username")
    if not username:
        return redirect("/login")

    avatar = request.form.get("avatar", "(´・ω・`)")
    bio = request.form.get("bio", "")[:100]

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("UPDATE users SET avatar=?, bio=? WHERE username=?", (avatar, bio, username))
    conn.commit()
    conn.close()

    return redirect("/account")


@main.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。")
    return redirect(url_for("main.login"))


@main.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("main.login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (session["user_id"],))
    conn.commit()
    conn.close()
    session.clear()
    flash("アカウントを削除しました。")
    return redirect(url_for("main.register"))


@main.route("/archive")
def archive():
    return render_template("archive.html")
