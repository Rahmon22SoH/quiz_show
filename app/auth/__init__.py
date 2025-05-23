from flask import Blueprint

auth = Blueprint('auth', __name__)

# Импортируем views *после* создания объекта Blueprint.
from app.auth import views
from .telegram import telegram_auth

# Регистрируем blueprint для Telegram аутентификации
auth.register_blueprint(telegram_auth, url_prefix='/telegram')