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

game_rooms = {}
suits = ["D", "H", "S", "K"]
numbers = list(range(1, 14))
cards = [f"{s}{n}" for s in suits for n in numbers]
def generate_deck():
    suits = ["H", "S", "D", "K"]
    return [f"{s}{i}" for s in suits for i in range(1, 14)] 

#一番最初
@socketio.on("join_game")
def handle_join(data):
    room = data["room"]
    username = data["username"]
    join_room(room)

    # 初期化（部屋が存在しない場合のみ）
    if room not in game_rooms:
        # 山札を作成・シャッフル
        deck = generate_deck()  # 例: ["H1", "H2", ..., "S13"]
        random.shuffle(deck)

        # 各プレイヤーに13枚ずつ配る
        all_hands = [deck[i*13:(i+1)*13] for i in range(4)]

        # 13×4のテーブル（スート別）
        table = {
            "hearts": [None] * 13,
            "spades": [None] * 13,
            "diamonds": [None] * 13,
            "clubs": [None] * 13
        }

        # 部屋の情報を初期化
        game_rooms[room] = {
            "players": [],
            "hands": {},
            "table": table,
            "deck": deck,
            "all_hands": all_hands,
            "turn_order": [],
            "current_turn": None,
            "passes": { "COM1": 0, "COM2": 0 }
        }

        cpu_names = ["COM1", "COM2"]
        game_rooms[room]["players"].extend(cpu_names)

        for i, cpu in enumerate(cpu_names):
            hand = all_hands[i]
            game_rooms[room]["hands"][cpu] = hand

        print(f"CPUプレイヤー: {cpu_names} を追加しました")

        # 7を中央に配置する
        #for suit in ["hearts", "spades", "diamonds", "clubs"]:
        #    table[suit][6] = None  # index=6 が「7」の位置（1始まり→0始まりで6）


    # 既存データ取得
    room_data = game_rooms[room]
    players = room_data["players"]
    table = room_data["table"]
    turn = room_data["current_turn"]

    # プレイヤー登録と手札割り当て
    if username not in players:
        players.append(username)
        idx = len(players)-1
        player_hand = room_data["all_hands"][idx]
        room_data["hands"][username] = player_hand
        room_data["passes"][username] = 0
    else:
        player_hand = room_data["hands"][username]

    suit_map = {"H": "hearts", "S": "spades", "D": "diamonds", "K": "clubs"}

    # 自分の手札から7を探してテーブルに置く
    new_hand = []
    for card in player_hand:
        suit = card[0]  # 例: "H7" → "H"
        num = int(card[1:])

        if num == 7:
            suit_name = suit_map[suit]
            table[suit_name][6] = card  # 7を中央に配置
            print(f"{username} が {card} を中央に配置しました")
        else:
            new_hand.append(card)

    # --- CPU側も7を配置 ---
    for cpu_name in ["COM1", "COM2"]:
        cpu_hand = room_data["hands"][cpu_name]
        new_cpu_hand = []
        for card in cpu_hand:
            suit = card[0]
            num = int(card[1:])
            if num == 7:
                suit_name = suit_map[suit]
                table[suit_name][6] = card
                print(f"{cpu_name} が {card} を中央に配置しました")
            else:
                new_cpu_hand.append(card)
        room_data["hands"][cpu_name] = new_cpu_hand
    
    # 手札更新
    room_data["hands"][username] = new_hand

    if room_data["current_turn"] is None:
        room_data["turn_order"] = random.sample(room_data["players"], len(room_data["players"]))
        room_data["current_turn"] = room_data["turn_order"][0]
        emit("announce_turn", {"player": room_data["current_turn"]}, to=room)
        print(f"先行プレイヤー: {room_data['current_turn']}")

    playable_cards = get_playable_cards(new_hand, table)

    print("テーブル : ", table)
    # 状態を全員に共有
    emit("update_table", {"table": table}, to=room)
    emit("update_hand", {"username": username, "hand": new_hand, "playable": playable_cards, "current_turn" : turn}, room=room)

#CPUの操作
def process_turn(room):
    room_data = game_rooms[room]
    current = room_data["current_turn"]
    table = room_data["table"]

    # ==== プレイヤーの番ならそのまま待つ ====
    if not current.startswith("COM"):
        return

    hand = room_data["hands"][current]
    playable = get_playable_cards(hand, table)

    if playable:
        card = random.choice(playable)
        print(f"🤖 {current} が {card} を提出します")
        handle_play_card({"username": current, "room": room, "card": card})
    else:
        print(f"🤖 {current} はパスします")
        # ターンだけ進める
        order = room_data["turn_order"]
        i = order.index(current)
        room_data["current_turn"] = order[(i+1) % len(order)]
        emit("announce_turn", {"player": room_data["current_turn"]}, to=room)

        # 次も COM なら続行
        process_turn(room)

#出せるカード
def get_playable_cards(hand, table):
    suit_map = {"H": "hearts", "S": "spades", "D": "diamonds", "K": "clubs"}
    playable = []

    for card in hand:
        suit = suit_map[card[0]]
        num = int(card[1:])  # 1～13
        row = table[suit]    # 例: ['None', ... , 'H7', ...]
        index = num - 1      # 1始まり → 0始まりへ

        if num == 7:
            continue  # 7は既に出してあるので手札には無いはず

        # 8〜13 → 左側（num-2）が埋まっているか
        if num > 7 and row[index - 1] is not None:
            playable.append(card)
            continue

        # 1〜6 → 右側（num）が埋まっているか
        if num < 7 and row[index + 1] is not None:
            playable.append(card)
            continue

    return playable

#ゲーム進行係
@socketio.on("play_card")
def handle_play_card(data):
    username = data["username"]
    room = data["room"]
    card = data["card"]

    room_data = game_rooms[room]
    table = room_data["table"]
    hand = room_data["hands"][username]

    suit_map = {"H": "hearts", "S": "spades", "D": "diamonds", "K": "clubs"}
    suit = suit_map[card[0]]
    num = int(card[1:])
    index = num - 1

    # --- カードを場に置く ---
    table[suit][index] = card

    # --- 手札から削除 ---
    if card in hand:
        hand.remove(card)

    # --- 次のターンへ進める ---
    order = room_data["turn_order"]
    current = room_data["current_turn"]
    next_index = (order.index(current) + 1) % len(order)
    room_data["current_turn"] = order[next_index]

    # --- 新しい手札の出せるカードを計算 ---
    playable = get_playable_cards(hand, table)

    # --- 画面更新を全員に送信 ---
    emit("update_table", {"table": table}, to=room)
    emit("update_hand", {"username": username, "hand": hand, "playable": playable}, to=room)
    emit("announce_turn", {"player": room_data["current_turn"]}, to=room)

    print(f"{username} が {card} を提出しました → 次は {room_data['current_turn']}")
    process_turn(room)

#パス処理
@socketio.on("pass_turn")
def handle_pass(data):
    username = data["username"]
    room = data["room"]

    room_data = game_rooms[room]

    # パス回数増加（3回超えたらパス不可 ※ 実際は UI 側で押せないようにする）
    room_data["passes"][username] += 1
    print(f"{username} はパスしました（現在: {room_data['passes'][username]}回）")

    # ターンを回す
    order = room_data["turn_order"]
    current = room_data["current_turn"]
    next_index = (order.index(current) + 1) % len(order)
    room_data["current_turn"] = order[next_index]

    emit("announce_turn", {
        "player": room_data["current_turn"],
        "passes": room_data["passes"]
    }, to=room)

    # COMなら自動進行
    process_turn(room)


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

"""
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
"""


# ----------------------------
# Render/Gunicorn 実行
# ----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
