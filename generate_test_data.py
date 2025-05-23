from app import create_app
from app.models import QuizSession, QuizParticipant, User, QuizWinners, Log
from app.extensions import db
from datetime import datetime, timedelta
import random
import string
import logging
from sqlalchemy.exc import SQLAlchemyError

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from tqdm import tqdm
    use_tqdm = True
except ImportError:
    use_tqdm = False

app = create_app()
app.app_context().push()

# --- Очистка старых данных ---
def clear_data():
    logger.info("Очистка старых тестовых данных...")
    try:
        # Удаляем участников квизов
        num_participants_deleted = QuizParticipant.query.delete()
        num_winners_deleted = QuizWinners.query.delete()
        # Удаляем сессии квизов
        num_quizzes_deleted = QuizSession.query.delete()
        # Удаляем логи только для тестовых пользователей
        test_user_ids = [u.id for u in User.query.filter(User.username.like('testuser%')).all()]
        num_logs_deleted = 0
        if test_user_ids:
            num_logs_deleted = Log.query.filter(Log.user_id.in_(test_user_ids)).delete(synchronize_session=False)
        # Удаляем тестовых пользователей
        num_users_deleted = User.query.filter(User.username.like('testuser%')).delete()
        db.session.commit()
        logger.info(f"Удалено участников: {num_participants_deleted}")
        logger.info(f"Удалено победителей: {num_winners_deleted}")
        logger.info(f"Удалено квизов: {num_quizzes_deleted}")
        logger.info(f"Удалено логов: {num_logs_deleted}")
        logger.info(f"Удалено тестовых пользователей: {num_users_deleted}")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Ошибка при очистке данных: {str(e)}")
        raise

def generate_random_string(length=8):
    """Генерация случайной строки."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def create_test_data():
    logger.info("Создание 100 тестовых пользователей...")
    users = []
    user_count = 100
    
    # Создаем пользователей с разными балансами
    for i in (tqdm(range(user_count), desc="Пользователи") if use_tqdm else range(user_count)):
        telegram_data = {
            'telegram_id': str(100000000 + i),
            'first_name': f'Test{i}',
            'last_name': f'User{i}',
            'username': f'testuser{i}',
            'auth_date': int(datetime.utcnow().timestamp()),
            'photo_url': f'https://example.com/photo_{i}.jpg'
        }
        user = User.get_or_create_from_telegram(telegram_data)
        try:
            user.set_password('testpass')
            # Устанавливаем случайный баланс от 1000 до 50000
            initial_balance = random.randint(10000, 50000)
            user.balance = initial_balance
            # Логируем установку начального баланса
            log = Log(
                user_id=user.id,
                action='initial_balance',
                details=f'Установлен начальный баланс: {initial_balance}₽',
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {i}: {str(e)}")
            continue
        users.append(user)
        if (i+1) % 100 == 0:
            try:
                db.session.commit()
                logger.info(f"Создано пользователей: {i+1}")
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Ошибка при сохранении пользователей: {str(e)}")
    
    try:
        db.session.commit()
        logger.info(f"Итого создано пользователей: {len(users)}")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Ошибка при финальном сохранении пользователей: {str(e)}")
        return

    quiz_count = 40
    logger.info(f"Создание {quiz_count} активных квизов (без участников)...")

    for i in (tqdm(range(quiz_count), desc="Квизы") if use_tqdm else range(quiz_count)):
        try:
            # Генерируем разную стоимость входа для квизов
            entry_fee = random.choice([5, 10, 25, 45, 55, 65, 75, 85, 95, 100, 150, 200])
            quiz = QuizSession(
                start_time=datetime.utcnow() - timedelta(minutes=i*10),
                end_time=datetime.utcnow() + timedelta(days=1),
                status='active',
                entry_fee=entry_fee,
                total_amount=0
            )
            db.session.add(quiz)
            db.session.commit()
            logger.info(f"Создан пустой квиз ID: {quiz.id} со стоимостью входа: {entry_fee}₽")

        except SQLAlchemyError as e:
            db.session.rollback()

    logger.info("Тестовые данные успешно созданы!")

if __name__ == '__main__':
    clear_data()
    create_test_data()