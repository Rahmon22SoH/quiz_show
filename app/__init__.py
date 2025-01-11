from flask import Flask
from config import Config
from app.extensions import db, migrate, mail, bootstrap, moment
from app.main import main as main_blueprint

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    # Регистрация Blueprint
    app.register_blueprint(main_blueprint)

    return app
