import os
from flask import Flask, request
from .routes import main
from flask_socketio import SocketIO, emit, join_room
from config import Config
import random, string
from app.database import init_db

rooms = {}

socketio = SocketIO(cors_allowed_origins="*")

room_players = {}
# ロビーごとの管理: { "password": [sid1, sid2, ...] }
waiting_rooms = {}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    from app.routes import main
    app.register_blueprint(main)

    socketio.init_app(app)
    return app

app = create_app()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# SocketIOの初期化
socketio = SocketIO(app, cors_allowed_origins="*")

#app = Flask(__name__)

# ✅ セッション暗号鍵（重要）
#app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ✅ DB 初期化
#with app.app_context():
#    init_db()

# ✅ Blueprintを登録
#from app.routes import main
#app.register_blueprint(main)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
