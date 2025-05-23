from flask import Blueprint

quiz = Blueprint('quiz', __name__)

# Импортируем только views
from app.quiz import views
