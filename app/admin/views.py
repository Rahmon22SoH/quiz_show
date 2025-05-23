from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.models import User, Log, QuizSession, QuizWinners, PlatformStats, QuizParticipant
from app.admin import admin
from app.extensions import db
from app.quiz.utils import pick_winner
from app.auth.auth_utils import admin_required
from app.celery.tasks import check_quiz_expiration, notify_quiz_started
from datetime import datetime, timedelta
from app.utils.error_handlers import handle_error
from app.profiling.decorators import profile_view
from app.utils.logger import log_info, log_warning, log_error, log_event, make_details
from flask_wtf import FlaskForm
from flask import current_app
from config import MOSCOW_UTC_OFFSET
from sqlalchemy import func
import io
import csv
from flask import Response
import time


@admin.route('/dashboard')
@admin_required
def dashboard():
    """Административная панель."""
    try:
        # Базовая статистика
        users_count = User.query.count()
        active_quizzes_count = QuizSession.query.filter_by(status='active').count()
        finished_quizzes_count = QuizSession.query.filter_by(status='finished').count()
        
        # Получаем или создаем объект статистики платформы
        platform_stats = PlatformStats.query.first()
        if not platform_stats:
            platform_stats = PlatformStats()
            db.session.add(platform_stats)
            db.session.commit()
        
        # Обновляем месячную статистику
        platform_stats.update_monthly_stats()
        
        # Дополнительная статистика для квизов
        
        # Средняя сумма квиза
        avg_quiz_amount = db.session.query(
            func.avg(QuizSession.total_amount)
        ).filter(
            QuizSession.status == 'finished'
        ).scalar() or 0
        
        # Квизы без участников
        empty_quizzes_count = QuizSession.query.filter_by(
            finished_without_participants=True
        ).count()
        
        # Квизы с одним участником
        single_participant_quizzes_count = QuizSession.query.filter_by(
            single_participant=True
        ).count()
        
        # Среднее количество участников в квизе
        avg_participants_count = db.session.query(
            func.avg(
                db.session.query(func.count(QuizParticipant.id))
                .filter(QuizParticipant.quiz_id == QuizSession.id)
                .correlate(QuizSession)
                .as_scalar()
            )
        ).filter(
            QuizSession.status == 'finished'
        ).scalar() or 0
        
        # Статистика пользователей
        active_users_count = db.session.query(
            func.count(func.distinct(QuizParticipant.user_id))
        ).scalar() or 0
        
        # Конверсия пользователей
        conversion_rate = active_users_count / users_count if users_count > 0 else 0
        
        # Общий баланс пользователей
        total_user_balance = db.session.query(
            func.sum(User.balance)
        ).scalar() or 0
        
        # Получаем последние действия (если этот код используется)
        recent_actions = Log.query.order_by(Log.timestamp.desc()).limit(10).all()
        
        return render_template(
            'admin/dashboard.html',
            users_count=users_count,
            active_quizzes_count=active_quizzes_count,
            finished_quizzes_count=finished_quizzes_count,
            platform_stats=platform_stats,
            avg_quiz_amount=int(avg_quiz_amount),
            empty_quizzes_count=empty_quizzes_count,
            single_participant_quizzes_count=single_participant_quizzes_count,
            avg_participants_count=round(avg_participants_count, 1),
            active_users_count=active_users_count,
            conversion_rate=conversion_rate,
            total_user_balance=total_user_balance
        )
    except Exception as e:
        flash('Ошибка при загрузке дашборда', 'error')
        return handle_error(e)

@admin.route('/users')
@admin_required
def view_users():
    """Просмотр пользователей."""
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        return handle_error(e)

@admin.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Изменение статуса пользователя (блокировка/разблокировка)."""
    try:
        log_event(
            action="admin_blocked_user",
            user_id=current_user.id,
            details=make_details(admin_id=current_user.id, blocked_user_id=user_id, ip=request.remote_addr),
            level="INFO",
            message="Администратор заблокировал пользователя",
            module=__name__,
            function="toggle_user_status"
        )
        user = User.query.get_or_404(user_id)
        
        log_info(f"Текущее состояние пользователя: active={user.active}, is_locked={user.is_locked}, is_active={user.is_active}")
        
        # Не позволяем блокировать самого себя
        if user.id == current_user.id:
            log_warning(f"Пользователь {current_user.username} пытается заблокировать себя")
            flash('Вы не можете заблокировать свою учетную запись', 'error')
            return redirect(url_for('admin.view_users'))
        
        # Инвертируем статус активности
        if user.is_active:
            # Если пользователь активен, блокируем его
            result = user.block()
            log_info(f"Блокировка пользователя: {result}")
        else:
            # Если пользователь неактивен, активируем его
            result = user.unblock()
            log_info(f"Разблокировка пользователя: {result}")
        
        log_info(f"Новое состояние пользователя: active={user.active}, is_locked={user.is_locked}, is_active={user.is_active}")
        
        # Логируем действие
        action = 'блокировка' if user.is_blocked else 'разблокировка'
        log_entry = Log(
            user_id=current_user.id,
            action=f'Изменение статуса пользователя',
            details=f'{action} пользователя {user.username} (ID: {user.id})'
        )
        
        # Сохраняем изменения в логе
        db.session.add(log_entry)
        db.session.commit()
        
        # Уведомление пользователя
        status_text = 'заблокирован' if user.is_blocked else 'разблокирован'
        flash(f'Пользователь {user.username} успешно {status_text}', 'success')
        
        return redirect(url_for('admin.view_users'))
    except Exception as e:
        db.session.rollback()
        log_error(f"Ошибка при изменении статуса пользователя: {str(e)}")
        flash(f'Произошла ошибка: {str(e)}', 'error')
        return redirect(url_for('admin.view_users'))

@admin.route('/quizzes')
@admin_required
def view_quizzes():
    """Просмотр списка квизов с фильтрацией и пагинацией."""
    try:
        # Получаем параметры из запроса
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status')
        per_page = 15  # Количество квизов на странице
        
        # Базовый запрос
        query = QuizSession.query
        
        # Применяем фильтр по статусу, если он указан
        if status_filter:
            query = query.filter(QuizSession.status == status_filter)
        
        # Сортируем по дате начала (сначала новые)
        query = query.order_by(QuizSession.start_time.desc())
        
        # Применяем пагинацию
        quizzes = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Преобразуем даты для отображения в МСК
        for quiz in quizzes.items:
            # Инициализируем атрибуты со значением None, если они не существуют
            if not hasattr(quiz, 'start_time_msk'):
                quiz.start_time_msk = None
            if not hasattr(quiz, 'end_time_msk'):
                quiz.end_time_msk = None
                
            # Устанавливаем значения, если есть исходные даты
            if quiz.start_time:
                quiz.start_time_msk = quiz.start_time + timedelta(hours=3)
            if quiz.end_time:
                quiz.end_time_msk = quiz.end_time + timedelta(hours=3)
            
        # Создаем форму для CSRF защиты
        form = FlaskForm()
        
        return render_template(
            'admin/quizzes.html',
            quizzes=quizzes,
            status_filter=status_filter,
            timedelta=timedelta,
            form=form  # Передаем форму в шаблон
        )
    except Exception as e:
        log_error(f"Ошибка при просмотре списка квизов: {str(e)}")
        flash(f'Произошла ошибка: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin.route('/quizzes/<int:quiz_id>/assign_winner', methods=['POST'])
@admin_required
def assign_winner(quiz_id):
    """Назначение победителя для завершенного квиза."""
    try:
        quiz = QuizSession.query.get_or_404(quiz_id)
        
        if quiz.status != 'finished':
            flash('Квиз должен быть завершен для назначения победителя.', 'warning')
            return redirect(url_for('admin.view_quizzes'))
            
        if quiz.winner_id:
            flash('У этого квиза уже есть победитель.', 'warning')
            return redirect(url_for('admin.view_quizzes'))
        
        # Проверяем наличие участников
        if quiz.participants.count() == 0:
            flash('Невозможно назначить победителя: в квизе нет участников.', 'warning')
            return redirect(url_for('admin.view_quizzes'))

        try:
            # Пробуем сначала асинхронно через Celery
            result = pick_winner.delay(quiz_id)
            flash('Задача выбора победителя запущена. Обновите страницу через несколько секунд.', 'info')
        except Exception as celery_error:
            # Если Celery недоступен, используем синхронную версию
            from app.quiz.utils import pick_winner_sync
            if pick_winner_sync(quiz_id):
                flash('Победитель успешно выбран.', 'success')
            else:
                flash('Ошибка при выборе победителя.', 'error')
            # Логируем ошибку Celery
            current_app.logger.error(f"Celery error in assign_winner: {str(celery_error)}")

        return redirect(url_for('admin.view_quizzes'))

    except Exception as e:
        flash('Ошибка при назначении победителя', 'error')
        return handle_error(e)

@admin.route('/quizzes/<int:quiz_id>/start', methods=['POST'])
@admin_required
def start_quiz(quiz_id):
    """Запускает квиз в статусе 'pending'."""
    quiz = QuizSession.query.get_or_404(quiz_id)
    if quiz.status != 'pending':
        flash('Этот квиз уже запущен или завершён.', 'warning')
        return redirect(url_for('admin.view_quizzes'))

    quiz.status = 'active'
    quiz.start_time = datetime.utcnow()
    db.session.commit()

    # Запуск рассылки уведомлений через Celery
    notify_quiz_started.delay(quiz.id)

    flash(f'Квиз {quiz.id} запущен! Уведомления отправляются пользователям.', 'success')
    return redirect(url_for('admin.view_quizzes'))

@admin.route('/quizzes/<int:quiz_id>/finish', methods=['POST'])
@admin_required
def finish_quiz(quiz_id):
    """Завершение квиза вручную."""
    try:
        quiz = QuizSession.query.get_or_404(quiz_id)
        if quiz.status == 'finished':
            flash('Этот квиз уже завершен.', 'warning')
            return redirect(url_for('admin.view_quizzes'))

        # Завершаем квиз
        quiz.status = 'finished'
        quiz.end_time = datetime.utcnow()
        quiz.finished_by_admin = True
        quiz.finished_by = current_user.id
        
        # Проверяем наличие участников
        if quiz.participants.count() == 0:
            # Если участников нет, отмечаем это в квизе
            quiz.finished_without_participants = True
            flash(f'Квиз {quiz.id} завершён без участников.', 'warning')
        else:
            flash(f'Квиз {quiz.id} завершён. Теперь вы можете выбрать победителя.', 'success')
        
        db.session.commit()

        log_event(
            action="admin_finished_quiz",
            user_id=current_user.id,
            details=make_details(admin_id=current_user.id, quiz_id=quiz_id, ip=request.remote_addr),
            level="INFO",
            message="Администратор завершил квиз вручную",
            module=__name__,
            function="finish_quiz"
        )

        return redirect(url_for('admin.view_quizzes'))

    except Exception as e:
        db.session.rollback()
        flash('Ошибка при завершении квиза', 'error')
        return handle_error(e)

@admin.route('/create_quiz', methods=['POST'])
@admin_required
def create_quiz():
    """Запуск нового квиза."""
    start = time.time()
    current_app.logger.info("[admin] START: create_quiz")
    try:
        form = FlaskForm()  # Создаем форму для CSRF защиты
        current_app.logger.info("[admin] Форма создана")
        # Проверяем валидность CSRF-токена
        if not form.validate_on_submit():
            current_app.logger.info("[admin] Форма не валидна")
            flash('Ошибка валидации формы: возможно, истек срок действия CSRF-токена. Пожалуйста, попробуйте снова.', 'error')
            return redirect(url_for('admin.view_quizzes'))
        current_app.logger.info("[admin] Форма валидна")
        # Получаем данные из формы
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
        entry_fee = request.form.get('entry_fee', type=int, default=100)
        current_app.logger.info(f"[admin] Даты и entry_fee получены: start_time={start_time}, end_time={end_time}, entry_fee={entry_fee}")
        # Проверяем валидность суммы входа
        if entry_fee < 5 or entry_fee > 10000:
            current_app.logger.info("[admin] Некорректная сумма entry_fee")
            flash('Сумма квиза должна быть равна от 5 до 10000 ₽', 'error')
            return redirect(url_for('admin.view_quizzes'))
        # Конвертируем время из МСК в UTC (МСК = UTC+3)
        start_time = start_time - timedelta(hours=3)
        end_time = end_time - timedelta(hours=3)
        current_app.logger.info(f"[admin] Даты сконвертированы в UTC: start_time={start_time}, end_time={end_time}")
        # Проверяем валидность дат
        now = datetime.utcnow()
        if start_time < now:
            current_app.logger.info("[admin] Дата начала в прошлом")
            flash('Дата начала не может быть в прошлом', 'error')
            return redirect(url_for('admin.view_quizzes'))
        if end_time <= start_time:
            current_app.logger.info("[admin] Дата окончания раньше даты начала")
            flash('Дата окончания должна быть позже даты начала', 'error')
            return redirect(url_for('admin.view_quizzes'))
        # Создаем новый квиз
        quiz = QuizSession(
            start_time=start_time,
            end_time=end_time,
            entry_fee=entry_fee,
            status='pending'
        )
        db.session.add(quiz)
        db.session.commit()
        current_app.logger.info(f"[admin] Квиз создан и закоммичен: quiz_id={quiz.id}")
        # Логируем создание квиза
        log = Log(
            user_id=current_user.id,
            action='create_quiz',
            details=f'Created quiz #{quiz.id} with entry fee {entry_fee}₽'
        )
        db.session.add(log)
        db.session.commit()
        current_app.logger.info(f"[admin] Лог создания квиза добавлен: log_id={log.id}")
        flash('Квиз успешно создан', 'success')
        current_app.logger.info(f"[admin] END: create_quiz, total: {time.time() - start:.2f}s")
        return redirect(url_for('admin.view_quizzes'))
    except ValueError as e:
        current_app.logger.error(f"[admin] Ошибка в формате даты: {str(e)}")
        flash('Ошибка в формате даты', 'error')
        return redirect(url_for('admin.view_quizzes'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[admin] Ошибка при создании квиза: {str(e)}")
        flash('Ошибка при создании квиза', 'error')
        return handle_error(e)

@admin.route('/logs')
@admin_required
def view_logs():
    """Просмотр логов из базы данных."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Фильтры
        level = request.args.get('level', None)
        module = request.args.get('module', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        search_query = request.args.get('search', None)
        
        # Базовый запрос
        query = Log.query
        
        # Применяем фильтры
        if level:
            query = query.filter(Log.level == level)
        if module:
            query = query.filter(Log.module == module)
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Log.timestamp >= start_date)
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                end_date = end_date + timedelta(days=1)  # Включаем весь день
                query = query.filter(Log.timestamp < end_date)
            except ValueError:
                pass
        if search_query:
            query = query.filter(
                db.or_(
                    Log.message.ilike(f'%{search_query}%'),
                    Log.details.ilike(f'%{search_query}%')
                )
            )
        
        # Получаем уникальные значения для фильтров
        unique_levels = db.session.query(Log.level).distinct().all()
        unique_modules = db.session.query(Log.module).distinct().all()
        
        # Статистика логов
        log_stats = {
            'error_count': Log.query.filter(Log.level == 'ERROR').count(),
            'warning_count': Log.query.filter(Log.level == 'WARNING').count(),
            'info_count': Log.query.filter(Log.level == 'INFO').count(),
            'debug_count': Log.query.filter(Log.level == 'DEBUG').count(),
            'critical_count': Log.query.filter(Log.level == 'CRITICAL').count(),
            'total_count': Log.query.count()
        }
        
        # Пагинация
        pagination = query.order_by(Log.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        logs = pagination.items
        
        return render_template(
            'admin/logs.html', 
            logs=logs, 
            pagination=pagination,
            unique_levels=[level[0] for level in unique_levels if level[0]],
            unique_modules=[module[0] for module in unique_modules if module[0]],
            selected_level=level,
            selected_module=module,
            start_date=start_date,
            end_date=end_date,
            log_stats=log_stats
        )
    except Exception as e:
        return handle_error(e)

@admin.route('/test-quiz-expiration')
@admin_required
def test_quiz_expiration():
    """Тестовый маршрут для проверки работы check_quiz_expiration."""
    task = check_quiz_expiration.delay()
    return f"Quiz expiration check started with task ID: {task.id}. Check console for results."

@admin.route('/winners')
@admin_required
def view_winners():
    """Просмотр победителей."""
    try:
        # Получаем параметры фильтрации
        quiz_id = request.args.get('quiz_id', type=int)
        user_id = request.args.get('user_id', type=int)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        page = request.args.get('page', 1, type=int)

        # Базовый запрос
        query = QuizWinners.query\
            .join(User, QuizWinners.user_id == User.id)\
            .join(QuizSession, QuizWinners.quiz_id == QuizSession.id)

        # Применяем фильтры
        if quiz_id:
            query = query.filter(QuizWinners.quiz_id == quiz_id)
        if user_id:
            query = query.filter(QuizWinners.user_id == user_id)
        if date_from:
            query = query.filter(QuizWinners.won_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(QuizWinners.won_at <= datetime.strptime(date_to, '%Y-%m-%d'))

        # Пагинация
        pagination = query.order_by(QuizWinners.won_at.desc()).paginate(
            page=page, per_page=20
        )

        # Получаем списки для фильтров
        quizzes = QuizSession.query.all()
        users = User.query.all()

        return render_template('admin/winners.html',
                             winners=pagination.items,
                             pagination=pagination,
                             quizzes=quizzes,
                             users=users)
    except Exception as e:
        return handle_error(e)

@admin.route('/winners/export')
@admin_required
def export_winners():
    """Экспорт истории выигрышей в CSV."""
    from io import StringIO
    import csv
    from flask import Response
    
    # Создаем CSV в памяти
    output = StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(['ID', 'Квиз', 'Победитель', 'Сумма', 'Дата'])
    
    # Данные
    winners = QuizWinners.query.join(User).join(QuizSession).all()
    for winner in winners:
        writer.writerow([
            winner.id,
            f'Квиз #{winner.quiz_id}',
            winner.user.username,
            winner.prize_amount,
            winner.won_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Создаем response
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=winners.csv'}
    )

@admin.route('/logs/export')
@admin_required
def export_logs():
    """Экспорт логов в CSV."""
    try:
        # Фильтры
        level = request.args.get('level', None)
        module = request.args.get('module', None)
        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        search_query = request.args.get('search', None)
        
        # Базовый запрос
        query = Log.query
        
        # Применяем фильтры
        if level:
            query = query.filter(Log.level == level)
        if module:
            query = query.filter(Log.module == module)
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Log.timestamp >= start_date)
            except ValueError:
                pass
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                end_date = end_date + timedelta(days=1)  # Включаем весь день
                query = query.filter(Log.timestamp < end_date)
            except ValueError:
                pass
        if search_query:
            query = query.filter(
                db.or_(
                    Log.message.ilike(f'%{search_query}%'),
                    Log.details.ilike(f'%{search_query}%')
                )
            )
        
        # Получаем все логи, соответствующие фильтрам
        logs = query.order_by(Log.timestamp.desc()).all()
        
        # Создаем CSV-файл
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow(['Время', 'Модуль', 'Уровень', 'Сообщение', 'Функция', 'Строка'])
        
        # Данные
        for log in logs:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.module,
                log.level,
                log.message or log.details,
                log.function,
                log.line
            ])
        
        # Создаем ответ
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    except Exception as e:
        return handle_error(e)

@admin.route('/get_csrf_token')
@admin_required
def get_csrf_token():
    """Получение CSRF-токена для API-запросов."""
    return jsonify({'csrf_token': generate_csrf()})

@admin.errorhandler(404)
def not_found_error(error):
    return render_template('admin/404.html'), 404

@admin.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('admin/500.html'), 500
