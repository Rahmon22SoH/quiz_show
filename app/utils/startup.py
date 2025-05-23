from app.auth.auth_utils import seed_roles_and_admin
from app.models import QuizSession  # Обновленный импорт
from app.extensions import db  # Импортируем db

def initialize_data(app):
    """Инициализируем данные при первом запросе."""
    with app.app_context():  # Добавляем контекст приложения
        seed_roles_and_admin()

def check_active_quiz(app):
    """Проверяем, есть ли активный квиз при старте приложения."""
    with app.app_context():  # Добавляем контекст приложения
        active_quiz = QuizSession.query.filter_by(status='active').first()
        if active_quiz:
            print(f"Найден активный квиз {active_quiz.id}, продолжаем его.")
        else:
            print("Активных квизов нет. Можно создать новый.") 