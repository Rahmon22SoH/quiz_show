from app import create_app
from app.models import QuizSession, QuizParticipant
from app.models import User
from app.extensions import db
from datetime import datetime, timedelta
import random
import time
from app.celery import celery

app = create_app()
app.app_context().push()
# Получаем экземпляр Celery
celery = app.extensions['celery']

def create_test_data():
    """Создаем тестовые данные для отладки"""
    try:
        # Создаем тестового пользователя если нет
        test_user = User.query.filter_by(email='test@test.com').first()
        if not test_user:
            test_user = User(
                username='test_user',
                email='test@test.com',
                first_name='Test',
                last_name='User',
                confirmed=True,
                balance=1000  # Добавляем начальный баланс
            )
            test_user.set_password('test123')
            db.session.add(test_user)
            db.session.commit()
            print(f"Created test user: {test_user.username}")

        # Создаем активный квиз с истекшим временем
        test_quiz = QuizSession(
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(minutes=5),
            status='active',
            total_amount=1000
        )
        db.session.add(test_quiz)
        db.session.commit()
        print(f"Created test quiz ID: {test_quiz.id}")

        # Добавляем участников
        for i in range(3):
            participant = QuizParticipant(
                quiz_id=test_quiz.id,
                user_id=test_user.id,
                amount=random.randint(100, 500)
            )
            db.session.add(participant)
        db.session.commit()
        print(f"Added {3} participants to quiz")

        return test_quiz.id
    except Exception as e:
        print(f"Error during execution: {str(e)}")

def debug_check_expiration():
    """Отладка задачи check_quiz_expiration"""
    from app.celery.tasks import check_quiz_expiration
    
    # Создаем тестовые данные
    quiz_id = create_test_data()
    
    print("\nStarting check_quiz_expiration task...")
    try:
        # Запускаем через Celery
        task = check_quiz_expiration.delay()
        print(f"Task ID: {task.id}")
        
        # Ждем результата
        print("Waiting for task completion...")
        time.sleep(10)  # Даем время на выполнение
        
        # Проверяем результат
        quiz = QuizSession.query.get(quiz_id)
        
        # Проверяем результат
        quiz = QuizSession.query.get(quiz_id)
        print(f"\nResults:")
        print(f"Quiz status: {quiz.status}")
        print(f"Winner ID: {quiz.winner_id}")
        if quiz.winner_id:
            winner = User.query.get(quiz.winner_id)
            print(f"Winner balance: {winner.balance}")
    except Exception as e:
        print(f"Error during execution: {str(e)}")

@celery.task
def debug_task():
    """Тестовая задача для отладки Celery."""
    print("Debug task is running...")
    return "Debug task completed"

if __name__ == '__main__':
    print("Starting Celery tasks debug...")
    debug_check_expiration()