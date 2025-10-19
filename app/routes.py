from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import os 

main = Blueprint("main", __name__, template_folder="templates")

# ---------------------------
# ホームなど既存ルート
# ---------------------------
@main.route('/')
def index():
    return render_template('index.html')

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
    if "user_id" not in session:
        flash("ログインしてください。")
        return redirect(url_for("main.login"))
    return render_template("account.html", username=session["username"])

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

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
