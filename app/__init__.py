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
            sid = player_sids.get(p)
            if sid:
                socketio.emit("match_found", {"room_id": room_id, "players": players}, to=sid)
                print("マッチングしました")
            else:
                print("sidなし")
    #broadcast_lobby_count()
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

game_rooms = []
suits = ["D", "H", "S", "K"]
numbers = list(range(1, 14))
cards = [f"{s}{n}" for s in suits for n in numbers]
def generate_deck():
    suits = ["H", "S", "D", "K"]
    return [f"{s}{i}" for s in suits for i in range(1, 14)] 

@socketio.on("join_game")
def handle_join(data):
    room = data["room"]
    username = data["username"]
    join_room(room)

    """
    if room not in game_rooms:
        game_rooms[room] = {
            "deck": generate_deck(),
            "players": {}, 
            "hands": {}, 
            "table": {"hearts":[], "spades":[], "diamonds":[], "clubs":[]}
            }  
    room_data = game_rooms[room]
    deck = room_data["deck"]
    print("デッキ:", deck)

    hands = room_data["hands"]

    if username not in hands:
        # デッキからランダムに13枚取り出す
        hand = random.sample(deck, 13)
        hands[username] = hand
        # デッキから削除
        for card in hand:
            deck.remove(card)

    # デバッグ用：各プレイヤーの配牌
    for u, h in hands.items():
        print(f"{u} の配牌: {h}")

    socketio.emit("update_hands", hands, room=room)
    print("hands : ", hands)
    # 全員に現在の手札を送信
    #socketio.emit("update_hands", players, room=room)
    """
    #テーブルもサーバー側で管理する。
    if room not in game_rooms:
        random.shuffle(cards)
        hands = [cards[i*13:(i+1)*13] for i in range(4)]
        table = [[None for _ in range(13)] for _ in range(4)]  # 13×4 のマス
        game_rooms[room] = {"players": [], "hands": {}, "table": table}

        for i, s in enumerate(suits):
            table[i][6] = f"{s}7"  # 中央(7列目)に7を配置

    # プレイヤー登録
    game_rooms[room]["players"].append(username)
    if username not in game_rooms[room]["hands"]:
        game_rooms[room]["hands"][username] = hands[len(game_rooms[room]["players"]) - 1]

    # 7を持っていた場合 → 自動でテーブルに置く
    player_hand = game_rooms[room]["hands"][username]
    for s in suits:
        seven = f"{s}7"
        if seven in player_hand:
            player_hand.remove(seven)
            # 7は中央列(6番目)に固定配置
            row = suits.index(s)
            game_rooms[room]["table"][row][6] = seven

    # 状態を全員に送信
    emit("update_table", {"table": game_rooms[room]["table"]}, to=room)
    emit("update_hand", {"username": username, "hand": player_hand}, room=room)

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
    game_rooms[room]["hands"][username].remove(card)
    suit = card[0]
    game_rooms[room]["table"][suit].append(card)
    emit("card_played", {"username": username, "card": card, "table": rooms[room]["table"]}, room=room)



# ----------------------------
# Render/Gunicorn 実行
# ----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
