from flask import Flask
from config import Config
from app.models import User
from flask_login import current_user
from flask_login import LoginManager
from app.extensions import db, migrate, mail, bootstrap, moment, login_manager
from app.main import main as main_blueprint
from app.auth import auth as auth_blueprint
from app.admin import admin as admin_blueprint
from .auth.auth_utils import seed_roles_and_admin
from app.auth import auth_utils
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' 
    
    @app.before_first_request
    def initialize_data():
        """Инициализируем данные при первом запросе."""
        seed_roles_and_admin()
    # Регистрация Blueprint
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(admin_blueprint, url_prefix='/admin')



    return app
