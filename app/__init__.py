from flask import Flask
from flask_socketio import SocketIO, join_room
from app.routes import main
from app.database import init_db
import os, threading, time

# Flask アプリ作成
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# DB 初期化
with app.app_context():
    init_db()

# Blueprint 登録
app.register_blueprint(main)

# SocketIO 初期化
socketio = SocketIO(app, cors_allowed_origins="*")

# ----------------------------
# マッチング用の変数
# ----------------------------
waiting_players = []
rooms = []
MAX_PLAYERS = 4
WAIT_TIME = 30  # 秒

# ----------------------------
# マッチング関数
# ----------------------------
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

# ----------------------------
# SocketIO イベント
# ----------------------------
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
# Render/Gunicorn 実行
# ----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
