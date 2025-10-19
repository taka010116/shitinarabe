from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, join_room, emit
import os, sqlite3, time, threading

# Flaskアプリを先に作る
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# SocketIOの初期化
socketio = SocketIO(app, cors_allowed_origins="*")

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

@main.route("/lobby")
def lobby():
    return render_template("lobby.html")

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
            return redirect(url_for("main.lobby"))  # ロビーへ移動
        else:
            flash("ユーザー名またはパスワードが間違っています。")
    return render_template("login.html")

# ----------------------------
# ロビーのSocketIO機能
# ----------------------------
waiting_players = []
rooms = []
MAX_PLAYERS = 4
WAIT_TIME = 30  # 秒

def start_matchmaking():
    """30秒経過したらCOMを追加してマッチングを開始"""
    global waiting_players
    if not waiting_players:
        return

    room_id = f"room_{int(time.time())}"
    players = waiting_players.copy()

    while len(players) < MAX_PLAYERS:
        players.append(f"COMPUTER_{len(players)+1}")

    rooms.append({"id": room_id, "players": players})
    waiting_players.clear()

    for p in players:
        if not p.startswith("COMPUTER"):
            socketio.emit("match_found", {"room_id": room_id, "players": players}, to=p)


@socketio.on("join_lobby")
def handle_join(data):
    """ロビーに参加"""
    username = data.get("username")
    if username not in waiting_players:
        waiting_players.append(username)
        join_room(username)
        print(f"{username} joined the lobby.")

    if len(waiting_players) == MAX_PLAYERS:
        start_matchmaking()
    elif len(waiting_players) == 1:
        threading.Timer(WAIT_TIME, start_matchmaking).start()


# ----------------------------
# Blueprint登録
# ----------------------------
app.register_blueprint(main)

# ----------------------------
# Render実行エントリポイント
# ----------------------------
if __name__ == "__main__":
    init_db()
    socketio.run(app, host="0.0.0.0", port=10000, debug=True)
