import eventlet
eventlet.monkey_patch()

from flask import Flask
from app.routes import main
import os

app = Flask(__name__)
# セッションでflashを使うために必要
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Blueprint登録
app.register_blueprint(main)

with app.app_context():
    from app.database import init_db
    init_db()


if __name__ == "__main__":
    #from app.database import init_db
    #init_db()  # データベース初期化
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
