from app.models.quiz_winners import QuizWinners
from app.models.quiz_session import QuizSession
from app.models.quiz_participant import QuizParticipant
from app.models.user import User
from app.extensions import db
from app.celery import celery
import secrets
from datetime import datetime
import logging
import random
from flask import current_app

logger = logging.getLogger(__name__)

def pick_winner_sync(quiz_id):
    """
    Синхронная версия выбора победителя квиза.
    
    Эта функция выбирает случайного победителя среди участников квиза,
    создает запись о выигрыше и начисляет выигрыш на баланс пользователя.
    
    Args:
        quiz_id (int): ID квиза для выбора победителя
        
    Returns:
        QuizParticipant: Объект участника-победителя
        
    Raises:
        ValueError: Если квиз не найден, не завершен, или нет участников
        Exception: При ошибках базы данных или других непредвиденных ошибках
    """
    try:
        # Получаем квиз
        quiz = QuizSession.query.get(quiz_id)
        if not quiz:
            logger.error(f"Квиз {quiz_id} не найден")
            raise ValueError(f"Quiz {quiz_id} not found")

        # Проверяем статус
        if quiz.status != 'finished':
            logger.error(f"Квиз {quiz_id} не завершен. Текущий статус: {quiz.status}")
            raise ValueError(f"Quiz {quiz_id} is not finished")
            
        # Проверяем, не назначен ли уже победитель
        if quiz.winner_id:
            logger.warning(f"Квиз {quiz_id} уже имеет победителя: {quiz.winner_id}")
            raise ValueError(f"Quiz {quiz_id} already has a winner")

        # Получаем всех участников
        participants = QuizParticipant.query.filter_by(quiz_id=quiz_id).all()
        if not participants:
            logger.error(f"В квизе {quiz_id} нет участников")
            raise ValueError(f"No participants in quiz {quiz_id}")
            
        # Если только один участник, возвращаем ему его ставку без комиссии
        if len(participants) == 1:
            winner = participants[0]
            logger.info(f"В квизе {quiz_id} только один участник: {winner.user_id}. Возвращаем ставку без комиссии.")
            
            # Обновляем информацию о победителе в квизе
            quiz.winner_id = winner.user_id
            quiz.single_participant = True  # Отмечаем, что был только один участник
            logger.info(f"Обновлен winner_id в квизе {quiz_id}: {winner.user_id}")
            
            # Создаем запись о возврате ставки в истории выигрышей
            quiz_winner = QuizWinners(
                quiz_id=quiz_id,
                user_id=winner.user_id,
                prize_amount=quiz.entry_fee,  # Возвращаем только ставку
                won_at=datetime.utcnow(),
                is_refund=True  # Отмечаем, что это возврат ставки
            )
            logger.info(f"Создана запись о возврате ставки: квиз {quiz_id}, пользователь {winner.user_id}, сумма {quiz.entry_fee}")
            
            # Обновляем баланс участника (возвращаем ставку)
            previous_balance = winner.user.balance
            winner.user.balance += quiz.entry_fee
            logger.info(f"Обновлен баланс пользователя {winner.user_id}: {previous_balance} -> {winner.user.balance}")
            
            # Сохраняем изменения в базе данных
            db.session.add(quiz_winner)
            db.session.commit()
            logger.info(f"Изменения сохранены в базе данных для квиза {quiz_id}")
            
            return winner

        # Выбираем победителя случайным образом
        winner = random.choice(participants)
        logger.info(f"Выбран победитель для квиза {quiz_id}: пользователь {winner.user_id}")
        
        # Обновляем информацию о победителе в квизе
        quiz.winner_id = winner.user_id
        logger.info(f"Обновлен winner_id в квизе {quiz_id}: {winner.user_id}")

        # Рассчитываем комиссию платформы (15% от общей суммы)
        platform_fee = int(quiz.total_amount * 0.15)
        winner_amount = quiz.total_amount - platform_fee
        
        # Обновляем статистику платформы
        from app.models import PlatformStats
        stats = PlatformStats.query.first()
        if not stats:
            stats = PlatformStats(total_revenue=platform_fee)
            db.session.add(stats)
        else:
            stats.total_revenue += platform_fee
        
        logger.info(f"Комиссия платформы: {platform_fee}, сумма выигрыша: {winner_amount}")

        # Создаем запись о победителе в истории выигрышей
        quiz_winner = QuizWinners(
            quiz_id=quiz_id,
            user_id=winner.user_id,
            prize_amount=winner_amount,  # Сумма за вычетом комиссии
            platform_fee=platform_fee,   # Комиссия платформы
            won_at=datetime.utcnow()
        )
        logger.info(f"Создана запись о выигрыше: квиз {quiz_id}, пользователь {winner.user_id}, сумма {winner_amount}, комиссия {platform_fee}")

        # Обновляем баланс победителя
        previous_balance = winner.user.balance
        winner.user.balance += winner_amount  # Зачисляем сумму за вычетом комиссии
        logger.info(f"Обновлен баланс пользователя {winner.user_id}: {previous_balance} -> {winner.user.balance}")
        
        # Логируем информацию о выигрыше
        logger.info(f"Победитель выбран для квиза {quiz_id}: Пользователь {winner.user_id} выиграл {winner_amount} (комиссия: {platform_fee})")

        # Сохраняем изменения в базе данных
        db.session.add(quiz_winner)
        db.session.commit()
        logger.info(f"Изменения сохранены в базе данных для квиза {quiz_id}")

        return winner
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при выборе победителя для квиза {quiz_id}: {str(e)}")
        raise e

def pick_winner(quiz_id):
    """Асинхронная версия выбора победителя квиза."""
    try:
        return pick_winner_sync(quiz_id)
    except Exception as e:
        raise e

@celery.task(bind=True, name='app.quiz.utils.pick_winner')
def pick_winner(self, quiz_id):
    """Выбирает победителя квиза."""
    logger.info(f"Запуск задачи выбора победителя для квиза {quiz_id}...")
    
    try:
        with current_app.app_context():
            # Получаем квиз
            quiz = QuizSession.query.get(quiz_id)
            if not quiz:
                logger.error(f"Квиз {quiz_id} не найден")
                return f"Квиз {quiz_id} не найден"
                
            # Проверяем статус квиза
            if quiz.status != 'finished':
                logger.error(f"Квиз {quiz_id} не завершен, текущий статус: {quiz.status}")
                return f"Квиз {quiz_id} не завершен, текущий статус: {quiz.status}"
                
            # Проверяем, есть ли уже победитель
            if quiz.winner_id:
                logger.warning(f"У квиза {quiz_id} уже есть победитель: {quiz.winner_id}")
                return f"У квиза {quiz_id} уже есть победитель: {quiz.winner_id}"
                
            # Проверяем, есть ли участники
            participants_count = quiz.participants.count()
            if participants_count == 0:
                logger.info(f"Квиз {quiz_id} завершен без участников, победитель не может быть выбран")
                # Обновляем статус квиза, чтобы он не попадал в повторную обработку
                quiz.finished_without_participants = True
                db.session.commit()
                return f"Квиз {quiz_id} завершен без участников"
                
            # Получаем всех участников
            participants = quiz.participants.all()
            if not participants:
                logger.warning(f"У квиза {quiz_id} нет участников")
                return f"У квиза {quiz_id} нет участников"
                
            # Если только один участник, возвращаем ему его ставку без комиссии
            if len(participants) == 1:
                winner = participants[0]
                winner_user = User.query.get(winner.user_id)
                
                if not winner_user:
                    logger.error(f"Winner user {winner.user_id} not found")
                    return {"status": "error", "message": "Winner user not found"}
                
                logger.info(f"В квизе {quiz_id} только один участник: {winner.user_id}. Возвращаем ставку без комиссии.")
                
                try:
                    # Начинаем транзакцию
                    quiz.winner_id = winner.user_id
                    quiz.single_participant = True  # Отмечаем, что был только один участник
                    winner_user.balance += quiz.entry_fee  # Возвращаем только ставку
                    
                    # Создаем запись в истории победителей (с пометкой о возврате)
                    winner_record = QuizWinners(
                        quiz_id=quiz.id,
                        user_id=winner.user_id,
                        prize_amount=quiz.entry_fee,  # Возвращаем только ставку
                        won_at=datetime.utcnow(),
                        is_refund=True  # Отмечаем, что это возврат ставки
                    )
                    
                    db.session.add(winner_record)
                    db.session.commit()
                    
                    # Отправляем уведомление участнику
                    try:
                        send_email(
                            winner_user.email,
                            'Возврат ставки',
                            'email/refund_notification',
                            user=winner_user,
                            amount=quiz.entry_fee,
                            quiz_id=quiz.id
                        )
                    except Exception as email_error:
                        logger.error(f"Ошибка при отправке email о возврате: {str(email_error)}")
                    
                    return {
                        "status": "success", 
                        "message": f"Квиз {quiz_id} завершен с одним участником. Ставка возвращена.",
                        "winner_id": winner.user_id,
                        "refund": True
                    }
                    
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error processing single participant refund: {str(e)}")
                    return {"status": "error", "message": str(e)}
                
            # Выбираем победителя
            winner = secrets.choice(participants)
            winner_user = User.query.get(winner.user_id)
            
            if not winner_user:
                logger.error(f"Winner user {winner.user_id} not found")
                return {"status": "error", "message": "Winner user not found"}

            try:
                # Рассчитываем комиссию платформы (15% от общей суммы)
                platform_fee = int(quiz.total_amount * 0.15)
                winner_amount = quiz.total_amount - platform_fee
                
                # Обновляем статистику платформы
                from app.models import PlatformStats
                stats = PlatformStats.query.first()
                if not stats:
                    stats = PlatformStats(total_revenue=platform_fee)
                    db.session.add(stats)
                else:
                    stats.total_revenue += platform_fee
                
                logger.info(f"Комиссия платформы: {platform_fee}, сумма выигрыша: {winner_amount}")
                
                # Начинаем транзакцию
                quiz.winner_id = winner.user_id
                winner_user.balance += winner_amount  # Зачисляем сумму за вычетом комиссии
                
                # Создаем запись в истории победителей
                winner_record = QuizWinners(
                    quiz_id=quiz.id,
                    user_id=winner.user_id,
                    prize_amount=winner_amount,  # Сумма за вычетом комиссии
                    platform_fee=platform_fee,   # Комиссия платформы
                    won_at=datetime.utcnow()
                )
                
                db.session.add(winner_record)
                db.session.commit()
                
                return {
                    "status": "success", 
                    "message": f"Победитель для квиза {quiz_id} выбран успешно",
                    "winner_id": winner.user_id,
                    "amount": winner_amount,
                    "platform_fee": platform_fee
                }
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error processing winner: {str(e)}")
                return {"status": "error", "message": str(e)}
                
    except Exception as e:
        logger.error(f"Error in pick_winner task: {str(e)}")
        return {"status": "error", "message": str(e)}
