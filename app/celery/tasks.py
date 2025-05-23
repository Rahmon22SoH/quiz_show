from datetime import datetime, timedelta
from app.extensions import db
from app.models import QuizSession, QuizParticipant, QuizWinners
from app.models import User, NotificationLog
from app.quiz.utils import pick_winner
from app.celery import celery
from flask import current_app
from app.utils.logger import log_event, make_details
import time
import logging
import requests
from app.utils.logger import log_event
from app.models.log import Log

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='app.celery.tasks.check_quiz_expiration')
def check_quiz_expiration(self):
    """Проверяет и завершает активные квизы, у которых истекло время."""
    logger.info("Запуск задачи проверки истечения времени квизов...")
    
    try:
        with current_app.app_context():
            # Получаем активные квизы для статистики на дашборде
            active_quizzes = QuizSession.query.filter_by(status='active').all()
            logger.info(f"Найдено {len(active_quizzes)} активных квизов")
            
            # Получаем квизы, требующие обработки:
            # 1. Активные квизы, которые могут истечь
            # 2. Завершенные квизы без победителя (не завершенные админом)
            quizzes_to_check = QuizSession.query.filter(
                db.or_(
                    QuizSession.status == 'active',
                    db.and_(
                        QuizSession.status == 'finished',
                        QuizSession.winner_id.is_(None),
                        # Проверяем только автоматически завершенные квизы
                        db.or_(
                            QuizSession.finished_by_admin.is_(False),
                            QuizSession.finished_by_admin.is_(None)
                        )
                    )
                )
            ).all()
            
            logger.info(f"Найдено {len(quizzes_to_check)} квизов для проверки")
            
            processed_quizzes = 0
            for quiz in quizzes_to_check:
                try:
                    logger.info(f"\nПроверка квиза {quiz.id}:")
                    logger.info(f"Время окончания (UTC): {quiz.end_time}")
                    logger.info(f"Текущее время (UTC): {datetime.utcnow()}")
                    
                    # Если квиз активен и истек срок
                    if quiz.status == 'active' and quiz.is_expired():
                        logger.info(f"Квиз {quiz.id} истек, завершаем...")
                        
                        # Обновляем статус квиза
                        quiz.status = 'finished'
                        quiz.finished_by_admin = False  # Отмечаем, что завершен автоматически
                        db.session.commit()
                        
                        # Запускаем асинхронную задачу выбора победителя
                        pick_winner.delay(quiz_id=quiz.id)
                        
                        processed_quizzes += 1
                        logger.info(f"Квиз {quiz.id} успешно завершен")
                        
                        # Логируем событие
                        log_event(
                            action="quiz_finished",
                            user_id=quiz.owner_id,
                            details=make_details(user_id=quiz.owner_id, quiz_id=quiz.id),
                            level="INFO",
                            message="Квиз завершён автоматически",
                            module=__name__,
                            function="check_quiz_expiration"
                        )
                    
                    # Если квиз завершен, но без победителя и не был завершен админом
                    elif quiz.status == 'finished' and not quiz.winner_id and not quiz.finished_by_admin:
                        logger.info(f"Квиз {quiz.id} завершен, но без победителя. Выбираем победителя...")
                        # Проверяем, есть ли участники
                        participants_count = quiz.participants.count()
                        if participants_count == 0:
                            logger.info(f"Квиз {quiz.id} завершен без участников, победитель не может быть выбран")
                            quiz.finished_without_participants = True
                            db.session.commit()
                            processed_quizzes += 1
                            continue
                        
                        pick_winner.delay(quiz_id=quiz.id)
                        processed_quizzes += 1
                        logger.info(f"Задача выбора победителя запланирована для квиза {quiz.id}")
                        
                except Exception as e:
                    logger.error(f"Ошибка при обработке квиза {quiz.id}: {str(e)}")
                    continue

            return f"Обработано {processed_quizzes} квизов"
    except Exception as e:
        logger.critical(f"Критическая ошибка в check_quiz_expiration: {str(e)}")
        return str(e)

@celery.task(name='app.celery.tasks.test_task')
def test_task():
    """Тестовая задача для проверки работы Celery."""
    time.sleep(5)
    return "Test task completed successfully!"

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_quiz_started(self, quiz_id, admin_id=None):
    """Рассылка уведомлений о старте квиза всем активным пользователям."""
    try:
        with current_app.app_context():
            quiz = QuizSession.query.get(quiz_id)
            if not quiz:
                return

            entry_fee = quiz.entry_fee
            # Используем серверное время окончания квиза, без смещения и без "МСК"
            end_time_str = quiz.end_time.strftime('%d.%m.%Y %H:%M')
            message = (
                f"Стартовал квиз! Испытай свою удачу.\n"
                f"Вход: {entry_fee}₽\n"
                f"Дата закрытия: {end_time_str}"
            )

            # Получаем токен Telegram-бота
            bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                current_app.logger.error("TELEGRAM_BOT_TOKEN не задан в конфиге!")
                return

            # Получаем всех пользователей, которым нужно отправить уведомление
            users = User.query.filter(
                User.active == True,
                User.is_locked == False,
                User.notifications_enabled == True,
                User.telegram_id.isnot(None)
            ).all()

            for user in users:
                status = 'success'
                error_text = None
                try:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        "chat_id": user.telegram_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }
                    resp = requests.post(url, json=payload, timeout=10)
                    if resp.status_code != 200 or not resp.json().get('ok'):
                        status = 'error'
                        error_text = resp.text
                        raise Exception(f"Telegram API error: {resp.text}")
                except Exception as exc:
                    status = 'error'
                    error_text = str(exc)
                    try:
                        self.retry(exc=exc)
                    except self.MaxRetriesExceededError:
                        pass  # Не прерываем цикл, просто логируем ошибку

                # Логируем попытку
                log = NotificationLog(
                    user_id=user.id,
                    quiz_id=quiz.id,
                    message=message if status == 'success' else f"{message}\n[ERROR]: {error_text}",
                    status=status,
                    timestamp=datetime.utcnow(),
                    transport='telegram'
                )
                db.session.add(log)
                db.session.commit()
                # Чтобы не превышать лимиты Telegram (30 сообщений/сек)
                time.sleep(0.04)

            log_event(
                action="quiz_start_notification_sent",
                user_id=admin_id,
                details=make_details(quiz_id=quiz_id, admin_id=admin_id),
                level="INFO",
                message="Уведомление о старте квиза успешно разослано",
                module=__name__,
                function="notify_quiz_started"
            )
    except Exception as e:
        log_event(
            action="quiz_start_notification_failed",
            user_id=admin_id,
            details=make_details(quiz_id=quiz_id, admin_id=admin_id, error=str(e)),
            level="ERROR",
            message=f"Ошибка при рассылке уведомления о старте квиза: {e}",
            module=__name__,
            function="notify_quiz_started"
        )
        raise

@celery.task(name='app.celery.tasks.cleanup_old_logs')
def cleanup_old_logs():
    """Удаляет бизнес-логи старше 2 месяцев."""
    threshold = datetime.utcnow() - timedelta(days=60)
    deleted = Log.query.filter(Log.timestamp < threshold).delete(synchronize_session=False)
    db.session.commit()
    log_event(
        action="logs_cleanup",
        user_id=None,
        details=make_details(deleted=deleted, threshold=str(threshold)),
        level="INFO",
        message=f"Автоматически удалено {deleted} логов старше 2 месяцев",
        module=__name__,
        function="cleanup_old_logs"
    )
    return deleted