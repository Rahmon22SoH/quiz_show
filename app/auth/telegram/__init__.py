from flask import Blueprint

telegram_auth = Blueprint('telegram_auth', __name__)

from . import views  # Импортируем представления
