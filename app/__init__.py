from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room, emit
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
def broadcast_lobby_count():
    socketio.emit("update_lobby_count", {"count": len(waiting_players)}, broadcast=True)


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

    broadcast_lobby_count()
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

from flask_socketio import join_room, leave_room, emit

rooms = {}  # room_id -> {"players": [username], "hands": {username: [cards]}, "table": {...}}


@socketio.on("disconnect")
def handle_disconnect():
    """ロビーから離脱"""
    # NOTE: 誰が切断したかを判定するのは難しいので単純化
    if waiting_players:
        waiting_players.pop()
        broadcast_lobby_count()  # ✅ ロビー人数を更新



@socketio.on("join_game")
def handle_join(data):
    room = data["room"]
    username = data["username"]
    join_room(room)
    if room not in rooms:
        rooms[room] = {"players": [], "hands": {}, "table": {"hearts":[], "spades":[], "diamonds":[], "clubs":[]}}  
    rooms[room]["players"].append(username)
    # ランダムで手札を配布（例: 13枚ずつ）
    deck = [f"{suit}{num}" for suit in ["H","S","D","C"] for num in range(1,14)]
    random.shuffle(deck)
    rooms[room]["hands"][username] = deck[:13]
    emit("update_hands", rooms[room]["hands"], room=room)

@socketio.on("play_card")
def handle_play(data):
    room = data["room"]
    username = data["username"]
    card = data["card"]
    # ここで場のルールチェック（7からの連番）
    # 場に出せる場合だけ
    rooms[room]["hands"][username].remove(card)
    suit = card[0]
    rooms[room]["table"][suit].append(card)
    emit("card_played", {"username": username, "card": card, "table": rooms[room]["table"]}, room=room)



# ----------------------------
# Render/Gunicorn 実行
# ----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
