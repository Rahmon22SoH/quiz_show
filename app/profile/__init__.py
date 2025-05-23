from flask import Blueprint

# Создаем Blueprint для профиля
profile = Blueprint('profile', __name__)

# Импортируем views *после* создания объекта Blueprint.
from app.profile import views 