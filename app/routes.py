from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, emit
import os, sqlite3, time, threading
import psycopg2

# Flaskアプリを先に作る
#app = Flask(__name__)
#app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# SocketIOの初期化
#socketio = SocketIO(app, cors_allowed_origins="*")

# Blueprint定義
main = Blueprint("main", __name__, template_folder="templates")

app = Flask(__name__)
app.secret_key = "secret-key"  # セッション用キー

# 🔹 Renderの環境変数からデータベースURLを取得
DATABASE_URL = "postgresql://takanami:NknWfypeq70O4aKab0tHZTXXKdGsJz3b@dpg-d3u927uuk2gs73dm85kg-a.oregon-postgres.render.com/mydb_6t0u"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    print("getDB")
    return conn



# ----------------------------
# ルート定義（ここから下）
# ----------------------------
@main.route("/")
def index():
    return render_template("index.html")

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

        conn = get_db_connection()
        cur = conn.cursor()

        # 同名ユーザーの存在確認
        cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            flash("このユーザー名はすでに使われています。")
        else:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (username, password))
            conn.commit()
            flash("登録が完了しました！ログインしてください。")
            cur.close()
            conn.close()
            return redirect(url_for("main.login"))

        cur.close()
        conn.close()

    return render_template("register.html")

# 🔹 ログインページ（簡易版）
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s;", (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            flash(f"ようこそ、{username}さん！")
            return redirect(url_for("main.account"))
        else:
            flash("ユーザー名またはパスワードが違います。")

    return render_template("login.html")

@main.route("/account")
def account():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.account"))

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

@main.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (session["user_id"],))
    conn.commit()
    conn.close()

    session.clear()
    flash("アカウントを削除しました")
    return redirect(url_for("main.register"))


@main.route("/lobby")
def lobby():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))

    return render_template("lobby.html")  # ロビー画面

#ここからゲーム
@main.route("/game")
def game():
    if "user_id" not in session:
        flash("ログインしてください")
        return redirect(url_for("main.login"))
    return render_template("game.html", username=session["username"])



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
