from flask import Blueprint

main = Blueprint('main', __name__)

# Импортируем views и errors *после* создания объекта Blueprint.
from app.main import views, errors
