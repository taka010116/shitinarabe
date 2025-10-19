import eventlet
eventlet.monkey_patch()

from flask import Flask
from app.routes import main
import os

app = Flask(__name__)
# セッションでflashを使うために必要
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
print("DEBUG: SECRET_KEY =", app.secret_key)

# Blueprint登録
app.register_blueprint(main)
# **アプリ起動時に必ず DB 初期化**
from app.database import init_db
print("DEBUG: init_db() を実行します")
init_db()



if __name__ == "__main__":
    #from app.database import init_db
    #init_db()  # データベース初期化
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
