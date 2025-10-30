from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room, emit
from app.routes import main
from app.database import init_db
import os, threading, time
import random
import uuid

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

#socketio = SocketIO(app)
# ----------------------------
# マッチング用の変数
# ----------------------------
waiting_players = []
player_sids = {}
rooms = []
MAX_PLAYERS = 4
WAIT_TIME = 30  # 秒

# ----------------------------
# マッチング関数
# ----------------------------
def broadcast_lobby_count():
    print("count", len(waiting_players))
    print("🔹 ロビーにいるユーザー:", waiting_players)  # デバッグ用

    if len(waiting_players) > 1:
        start_matching()
        print("マッチング開始")
    
    socketio.emit(
        "update_lobby_info",
        {"count": len(waiting_players), "players": waiting_players},
        to=None
    )

def start_matching():
    """30秒経過したらCOMを追加してマッチングを開始"""
    global waiting_players
    #if not waiting_players:
    #    return

    room_id = f"room_{int(time.time())}"
    players = waiting_players[:MAX_PLAYERS]
    #players = waiting_players.copy()

    #while len(players) < MAX_PLAYERS:
    #    players.append(f"COMPUTER_{len(players)+1}")

    
    rooms.append({"id": room_id, "players": players})
    #rooms[room_id] = {"players": players, "hands": {}, "table": {"hearts":[], "spades":[], "diamonds":[], "clubs":[]}}

#waiting_players.clear()

    for p in players:
        if not p.startswith("COMPUTER"):
            socketio.emit("match_found", {"room_id": room_id, "players": players}, to=p)
            print("マッチングしました")
    broadcast_lobby_count()
# ----------------------------
# SocketIO イベント
# ----------------------------

@socketio.on("connect")
def handle_connect():
    print("🟢 Client connected")

@socketio.on("join_lobby")
def handle_join(data):
    """ロビー参加時の処理"""
    username = data.get("username")
    sid = request.sid
    player_sids[username] = sid
    print(f"🟢 {username}を入れる。")

    if username not in waiting_players:
        waiting_players.append(username)
        print("waitingに人を入れた")
        print(f"🟢 {username} joined the lobby")

    else:
        print("入れなかった")

    print(f"{username} joined the lobby. 現在の人数: {len(waiting_players)}")
    print(f"🔹 ロビーにいるユーザー: {waiting_players}")

    join_room("lobby")
    socketio.emit(
        "update_lobby_info",
        {"count": len(waiting_players), "players": waiting_players},
        to=None
    )
    # 全員に人数を更新
    broadcast_lobby_count()
    
from flask_socketio import join_room, leave_room, emit

#rooms = {}  # room_id -> {"players": [username], "hands": {username: [cards]}, "table": {...}}


@socketio.on("disconnect")
def handle_disconnect():
    """プレイヤーが離脱"""
    sid = request.sid
    username = None
    # sid -> username の逆引き
    for s, u in player_sids.items():
        if s == sid:
            username = u
            break

    if username:
        print(f"🔴 {username} disconnected")
        if username in waiting_players:
            waiting_players.remove(username)
        player_sids.pop(username, None)

    broadcast_lobby_count()


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

@socketio.on("leave_lobby")
def handle_leave(data):
    """ロビー退出時の処理"""
    username = data.get("username")
    if username in waiting_players:
        waiting_players.remove(username)
        print(f"{username} left the lobby. 現在の人数: {len(waiting_players)}")
        broadcast_lobby_count()


@socketio.on("start_match")
def handle_start():
    """4人揃ったら自動でゲーム開始"""
    if len(waiting_players) >= 4:
        selected_players = waiting_players[:4]
        print("対局開始:", selected_players)

        # 残りの人をロビーに残す
        del waiting_players[:4]

        # 全員にゲーム開始通知
        socketio.emit("match_started", {"players": selected_players}, namespace="/")

        # 人数更新（残りのロビー人数を送信）
        broadcast_lobby_count()


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
