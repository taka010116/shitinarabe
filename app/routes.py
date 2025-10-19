from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, emit
import os, sqlite3, time, threading

# Flaskアプリを先に作る
#app = Flask(__name__)
#app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# SocketIOの初期化
#socketio = SocketIO(app, cors_allowed_origins="*")

# Blueprint定義
main = Blueprint("main", __name__, template_folder="templates")

# ----------------------------
# ルート定義（ここから下）
# ----------------------------
@main.route("/")
def index():
    return render_template("index.html")

@main.route("/game")
def game():
    return render_template("game.html")

#@main.route("/lobby")
#def lobby():
#    return render_template("lobby.html")

# ----------------------------
# データベース初期化
# ----------------------------
if not os.path.exists("users.db"):
    print("🗂 users.db が存在しないため作成します...")
    init_db()
else:
    print("✅ users.db は既に存在します")

# ----------------------------
# 登録・ログインなど
# ----------------------------
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
            return redirect(url_for("main.account"))  # ロビーへ移動
        else:
            flash("ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")

@main.route("/account")
def account():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))

    user_id = session["user_id"]
    username = session["username"]
    return render_template("account.html", user_id=user_id, username=username)

@main.route("/account/update", methods=["POST"])
def update_account():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))

    username = request.form["username"]
    # ここで DB 更新処理
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET username=? WHERE id=?", (username, session["user_id"]))
    conn.commit()
    conn.close()

    session["username"] = username  # セッション更新
    flash("アカウント情報を更新しました")
    return redirect(url_for("main.account"))

@main.route("/lobby")
def lobby():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))

    return render_template("lobby.html")  # ロビー画面
# ----------------------------
# ロビーのSocketIO機能
# ----------------------------

# ----------------------------
# Blueprint登録
# ----------------------------
#app.register_blueprint(main)

# ----------------------------
# Render実行エントリポイント
# ----------------------------
if __name__ == "__main__":
    init_db()
    #socketio.run(app, host="0.0.0.0", port=10000, debug=True)
