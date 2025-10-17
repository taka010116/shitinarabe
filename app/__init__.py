import os
from flask import Flask
from .routes import main
from config import Config

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    app.register_blueprint(main)

    return app

app = create_app()

if __name__ == "__main__":
    app.run()
