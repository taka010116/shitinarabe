from flask import Blueprint, redirect, url_for, render_template, flash, request, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import os

main = Blueprint("main", __name__, template_folder="templates")

# ホーム
@main.route("/")
def index():
    user = session.get("username")
    return render_template("index.html", user=user)

# 登録
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

# ログイン
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
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("ログイン成功！")
            return redirect(url_for("main.account"))
        else:
            flash("ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")

# マイページ
@main.route("/account", methods=["GET", "POST"])
def account():
    if "username" not in session:
        return redirect(url_for("main.login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (session["username"],))
    user = c.fetchone()
    conn.close()

    if request.method == "POST":
        avatar = request.form.get("avatar", "(´・ω・`)")[:50]
        bio = request.form.get("bio", "")[:100]  # 100文字制限
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET avatar=?, bio=? WHERE username=?", (avatar, bio, session["username"]))
        conn.commit()
        conn.close()
        flash("プロフィールを更新しました。")
        return redirect(url_for("main.account"))

    return render_template("account.html", user=user)

# ログアウト
@main.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。")
    return redirect(url_for("main.login"))

# アカウント削除
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
