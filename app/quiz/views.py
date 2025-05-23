from flask import Blueprint, jsonify, request, flash, redirect, url_for, render_template, current_app
from flask_login import current_user, login_required
from app.models import QuizSession, QuizParticipant, User
from app.extensions import db, cache, limiter
from datetime import datetime
from app.quiz import quiz
from flask_wtf import FlaskForm
from app.utils.error_handlers import handle_error
from config import MOSCOW_UTC_OFFSET
import sqlalchemy.exc
import time
from app.utils.logger import log_event, make_details


# Лимит на все GET-запросы профиля
limiter.limit("30 per minute", methods=["GET"])(quiz)

@quiz.route('/')
@login_required
@cache.cached(timeout=8, key_prefix=lambda: f"quiz_index_{current_user.get_id()}")  
def index():
    """Главная страница квизов."""
    start_time = time.time()
    try:
        # Оптимизированный запрос с использованием подзапроса
        subquery = db.session.query(
            QuizParticipant.quiz_id
        ).filter(
            QuizParticipant.user_id == current_user.id
        ).subquery()

        active_quizzes = db.session.query(
            QuizSession,
            db.exists().where(
                QuizSession.id == subquery.c.quiz_id
            ).label('user_participation')
        ).filter(
            QuizSession.status == 'active'
        ).order_by(
            QuizSession.start_time.desc()
        ).all()

        # Получаем id всех активных квизов
        quiz_ids = [quiz.id for quiz, _ in active_quizzes]
        participants_count = {}
        if quiz_ids:
            # Один запрос для подсчёта участников по каждому квизу
            counts = db.session.query(
                QuizParticipant.quiz_id,
                db.func.count(QuizParticipant.id)
            ).filter(
                QuizParticipant.quiz_id.in_(quiz_ids)
            ).group_by(QuizParticipant.quiz_id).all()
            participants_count = {quiz_id: count for quiz_id, count in counts}

        # Подготавливаем данные для отображения
        quizzes_data = []
        participated_quiz_ids = []
        available_quiz_ids = []
        for quiz, user_participation in active_quizzes:
            if user_participation:
                participated_quiz_ids.append(quiz.id)
            else:
                available_quiz_ids.append(quiz.id)
            quizzes_data.append({
                'id': quiz.id,
                'start_time': quiz.start_time.isoformat() if quiz.start_time else None,
                'end_time': quiz.end_time.isoformat() if quiz.end_time else None,
                'entry_fee': quiz.entry_fee,
                'total_amount': quiz.total_amount,
                'participants': participants_count.get(quiz.id, 0),
                'user_participation': user_participation,
                'status': quiz.status
            })

        # Безопасное расширенное логирование
        duration = round((time.time() - start_time) * 1000)  # ms
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', 'unknown')
        current_app.logger.info(
            f"Cache key for user_id={current_user.get_id()}: quiz_index_{current_user.get_id()}"
            f"Quiz index | user_id={current_user.get_id()} | ip={ip} | agent={user_agent} | "
            f"active_quiz_ids={quiz_ids} | count={len(quiz_ids)} | "
            f"participated_quiz_ids={participated_quiz_ids} | participated_count={len(participated_quiz_ids)} | "
            f"available_quiz_ids={available_quiz_ids} | available_count={len(available_quiz_ids)} | "
            f"duration_ms={duration}"
        )
        if current_app.debug:
            current_app.logger.debug(f"Quizzes data: {quizzes_data}")
        form = FlaskForm()
        result = render_template('quiz/index.html', active_quizzes=quizzes_data, form=form)
        duration = time.time() - start_time
        current_app.logger.info(f"Quiz index duration: {duration:.2f}s")
        return result
    except Exception as e:
        flash(f'Произошла ошибка: {str(e)}', 'error')
        return redirect(url_for('main.index'))

@quiz.route('/quizzes', methods=['GET'])
def get_active_quiz():
    """Заглушка: Получение активного квиза."""
    return jsonify({"message": "Текущий квиз ещё не реализован."}), 200

@quiz.route('/join/<int:quiz_id>', methods=['POST'])
@login_required
@limiter.limit("25 per minute")
def join_quiz(quiz_id):
    """
    Присоединение к квизу.
    Эта функция обрабатывает запрос на присоединение пользователя к квизу.
    Проверяет статус квиза, баланс пользователя, и создает запись об участии.
    Использует транзакционные блоки и блокировку строк для обеспечения атомарности
    и предотвращения гонки данных.
    Функция выполняет следующие основные операции:
    1. Проверка CSRF и валидация входных данных
    2. Предварительная проверка квиза, пользователя и участия (один запрос)
    3. Блокировка и обновление данных в транзакции
    4. Создание записи об участии и обновление балансов
    
    Args:
        quiz_id (int): ID квиза для присоединения
        
    Returns:
        Response: Перенаправление на страницу квизов с сообщением о результате
    """
    form = FlaskForm()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not form.validate_on_submit():
        current_app.logger.warning(f"Ошибка CSRF при присоединении к квизу. User: {current_user.id}")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Ошибка безопасности. Пожалуйста, обновите страницу и попробуйте снова.'}), 400
        flash('Ошибка безопасности. Пожалуйста, обновите страницу и попробуйте снова.', 'error')
        return redirect(url_for('quiz.index')) # Редирект на страницу квизов
    
    try:
        # Оптимизированный запрос: объединяем проверки квиза, пользователя и участия
        # Используем один запрос вместо нескольких отдельных запрос с явным указанием порядка JOIN-ов
        initial_check = db.session.query(
            QuizSession,
            User,
            QuizParticipant
        ).select_from(QuizSession).filter(
            QuizSession.id == quiz_id
        ).join(
            User,
            User.id == current_user.id
        ).outerjoin(
            QuizParticipant,
            db.and_(
                QuizParticipant.quiz_id == QuizSession.id,
                QuizParticipant.user_id == User.id
            )
        ).first()

        # Проверяем результаты начального запроса
        if not initial_check or not initial_check[0]:
            current_app.logger.error(f"Квиз {quiz_id} не найден")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Квиз не найден.'}), 404
            flash('Квиз не найден.', 'error')
            return redirect(url_for('quiz.index'))

        # Распаковываем результаты запроса
        quiz, user, existing_participant = initial_check

        # Проверка статуса квиза
        if quiz.status != 'active':
            current_app.logger.warning(f"Попытка присоединиться к неактивному квизу {quiz_id}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Этот квиз недоступен для участия.'}), 400
            flash('Этот квиз недоступен для участия.', 'warning')
            return redirect(url_for('quiz.index'))

        # Проверка существующего участия
        if existing_participant:
            current_app.logger.info(f"Пользователь {user.id} уже участвует в квизе {quiz_id}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Вы уже участвуете в этом квизе.'}), 200
            flash('Вы уже участвуете в этом квизе.', 'info')
            return redirect(url_for('quiz.index'))

        # Проверка баланса пользователя
        amount = quiz.entry_fee
        if user.balance < amount:
            current_app.logger.info(
                f"Недостаточно средств для участия. User: {user.id}, "
                f"Balance: {user.balance}, Required: {amount}"
            )
            if is_ajax:
                return jsonify({'success': False, 'message': f'Недостаточно средств на балансе. Необходимо: {amount}₽', 'redirect': url_for('profile.deposit', quiz_id=quiz_id)}), 402
            flash(f'Недостаточно средств на балансе. Необходимо: {amount}₽', 'warning')
            return redirect(url_for('profile.deposit', quiz_id=quiz_id))

        # Закрываем текущую сессию перед началом новой транзакции
        db.session.close()
        
        # Флаг успешного выполнения транзакции
        success = False
        
        try:
            # Используем контекстный менеджер для транзакции
            with db.session.begin():
                # Блокируем записи для обновления с явным указанием порядка
                locked_data = db.session.query(
                    QuizSession,
                    User
                ).select_from(QuizSession).filter(
                    QuizSession.id == quiz_id
                ).join(
                    User,
                    User.id == current_user.id
                ).with_for_update().first()

                if not locked_data:
                    raise Exception("Не удалось заблокировать записи")

                quiz, user = locked_data

                # Повторные проверки после блокировки
                if quiz.status != 'active':
                    raise ValueError("Квиз больше не активен")

                if user.balance < amount:
                    raise ValueError("Недостаточно средств")

                # Создаем запись об участии
                participant = QuizParticipant(
                    quiz_id=quiz_id,
                    user_id=user.id,
                    amount=amount,
                    joined_at=datetime.utcnow()
                )

                # Сохраняем предыдущие значения для логирования
                previous_balance = user.balance
                previous_total = quiz.total_amount
                
                # Обновляем баланс пользователя и призовой фонд квиза
                user.balance -= amount
                quiz.total_amount += amount
                
                # Добавляем нового участника
                db.session.add(participant)
                
                # Отмечаем успешное выполнение
                success = True

                # Логируем финансовую транзакцию
                current_app.logger.info(
                    f"Финансовая транзакция: User {user.id} присоединился к квизу {quiz_id}. "
                    f"Сумма: {amount}₽. Баланс: {previous_balance} -> {user.balance}. "
                    f"Призовой фонд: {previous_total} -> {quiz.total_amount}"
                )

        except ValueError as e:
            current_app.logger.warning(f"Ошибка валидации: {str(e)}")
            if is_ajax:
                return jsonify({'success': False, 'message': str(e)}), 400
            flash(str(e), 'warning')
            return redirect(url_for('main.index'))
            
        except sqlalchemy.exc.IntegrityError as e:
            current_app.logger.error(f"Ошибка целостности данных: {str(e)}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Ошибка при присоединении к квизу: нарушение целостности данных.'}), 409
            flash('Ошибка при присоединении к квизу: нарушение целостности данных.', 'error')
            return redirect(url_for('quiz.index'))
            
        except Exception as e:
            current_app.logger.error(f"Ошибка при присоединении к квизу: {str(e)}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Произошла ошибка при присоединении к квизу.'}), 500
            flash('Произошла ошибка при присоединении к квизу.', 'error')
            return redirect(url_for('quiz.index'))

        # Отображаем сообщение о результате операции
        if success:
            if is_ajax:
                return jsonify({'success': True, 'message': 'Вы успешно присоединились к квизу!', 'quiz_id': quiz_id}), 200
            flash('Вы успешно присоединились к квизу!', 'success')
        else:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Не удалось присоединиться к квизу.'}), 500
            flash('Не удалось присоединиться к квизу.', 'error')

        return redirect(url_for('quiz.index'))

    except Exception as e:
        current_app.logger.error(f"Критическая ошибка: {str(e)}")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Произошла неожиданная ошибка.'}), 500
        flash('Произошла неожиданная ошибка.', 'error')
        return redirect(url_for('quiz.index'))

@quiz.route('/_test/active_quizzes', methods=['GET'])
def get_test_active_quizzes():
    """Тестовый API-эндпоинт для получения списка активных квизов (только для debug)."""
    if not current_app.debug:
        current_app.logger.warning(f"Attempt to access debug endpoint /_test/active_quizzes in non-debug mode.")
        return jsonify({"error": "Not available in production"}), 403

    try:
        # Запрос к БД для получения ID и entry_fee активных квизов
        active_quizzes_data = db.session.query(
            QuizSession.id,
            QuizSession.entry_fee
        ).filter(
            QuizSession.status == 'active'
        ).order_by(QuizSession.id).all() # Order for consistency if needed

        # Преобразуем amount в строку, как в форме
        quizzes_list = [{'id': q_id, 'amount': str(fee)} for q_id, fee in active_quizzes_data]
        current_app.logger.debug(f"/_test/active_quizzes returning {len(quizzes_list)} quizzes.")
        return jsonify(quizzes_list)
    except Exception as e:
        current_app.logger.error(f"Error in /_test/active_quizzes: {str(e)}")
        return jsonify({"error": "Failed to fetch quiz data"}), 500

@quiz.route('/api/quiz/<int:quiz_id>/status', methods=['GET'])
def check_quiz_status(quiz_id):
    """API для проверки статуса квиза."""
    try:
        quiz = QuizSession.query.get_or_404(quiz_id)
        return jsonify({
            'status': quiz.status,
            'end_time': quiz.end_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if quiz.end_time else None
        })
    except Exception as e:
        current_app.logger.error(f"Ошибка при проверке статуса квиза {quiz_id}: {str(e)}")
        return jsonify({'error': 'Ошибка при проверке статуса квиза'}), 500
