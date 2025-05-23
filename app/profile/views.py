from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from app.profile import profile
from app.profile.forms import ProfileEditForm, BalanceOperationForm
from app.extensions import db, limiter
from app.utils.error_handlers import handle_error
from app.models import User, QuizParticipant, QuizWinners, QuizSession
from flask_wtf.csrf import validate_csrf
from app.utils.logger import log_event, make_details


# Лимит на все GET-запросы профиля
limiter.limit("30 per minute", methods=["GET"])(profile)

@profile.route('/')
@profile.route('/index/')
@login_required
def index():
    """Профиль пользователя."""
    try:
        page = request.args.get('page', 1, type=int)
        
        # Получаем все участия пользователя в квизах (включая выигрыши и проигрыши)
        participations_query = db.session.query(
            QuizParticipant,
            QuizSession,
            QuizWinners
        ).outerjoin(
            QuizSession, QuizParticipant.quiz_id == QuizSession.id
        ).outerjoin(
            QuizWinners, 
            db.and_(
                QuizWinners.quiz_id == QuizParticipant.quiz_id,
                QuizWinners.user_id == QuizParticipant.user_id
            )
        ).filter(
            QuizParticipant.user_id == current_user.id
        ).order_by(
            QuizParticipant.created_at.desc()
        )
        
        # Пагинация результатов
        pagination = participations_query.paginate(page=page, per_page=10, error_out=False)
        
        # Подготовка данных для шаблона
        participations = []
        for participant, quiz, winner in pagination.items:
            is_winner = winner is not None
            is_refund = False
            
            # Проверяем, был ли это возврат ставки
            if winner and hasattr(winner, 'is_refund'):
                is_refund = winner.is_refund
            
            participation_data = {
                'quiz_id': participant.quiz_id,
                'created_at': participant.created_at,
                'entry_fee': quiz.entry_fee,
                'is_winner': is_winner,
                'prize_amount': winner.prize_amount if is_winner else 0,
                'quiz_status': quiz.status,
                'is_refund': is_refund
            }
            
            participations.append(participation_data)
        
        # Статистика
        stats = {
            'total_games': QuizParticipant.query.filter_by(user_id=current_user.id).count(),
            'wins': QuizWinners.query.filter_by(user_id=current_user.id).count(),
            'last_game': db.session.query(db.func.max(QuizParticipant.created_at)).filter(
                QuizParticipant.user_id == current_user.id
            ).scalar()
        }
        
        current_app.logger.info(f"Current user: {current_user.id}")
        return render_template('profile/index.html',
                             user=current_user,
                             stats=stats,
                             participations=participations,
                             pagination=pagination)
    except Exception as e:
        current_app.logger.error(f"Error in profile index: {str(e)}")
        flash('Ошибка при загрузке профиля.', 'danger')
        return redirect(url_for('main.index'))

@profile.route('/update', methods=['POST'])
@limiter.limit("25 per minute")
@login_required
def update_profile():
    """Обновление данных профиля."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Обновляем только разрешенные поля
        allowed_fields = ['username', 'first_name', 'last_name']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400
            
        # Проверяем уникальность username если он меняется
        if 'username' in updates:
            existing_user = User.query.filter_by(username=updates['username']).first()
            if existing_user and existing_user.id != current_user.id:
                return jsonify({'error': 'Username already taken'}), 400
                
        # Обновляем профиль
        for key, value in updates.items():
            setattr(current_user, key, value)
            
        db.session.commit()
        
        log_event(
            action="profile_updated",
            user_id=current_user.id,
            details=make_details(user_id=current_user.id, ip=request.remote_addr, fields_changed="email,avatar"),
            level="INFO",
            message="Пользователь обновил профиль",
            module=__name__,
            function="update_profile"
        )
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'username': current_user.username,
                'first_name': current_user.first_name,
                'last_name': current_user.last_name
            }
        })
        
    except Exception as e:
        print(f"Error updating profile: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@profile.route('/profile/edit', methods=['GET', 'POST'])
@limiter.limit("25 per minute")
@login_required
def edit_profile():
    """Редактирование профиля пользователя"""
    form = ProfileEditForm()
    if form.validate_on_submit():
        # Проверяем уникальность username
        if form.username.data != current_user.username and \
           User.query.filter_by(username=form.username.data).first():
            flash('Это имя пользователя уже занято.', 'danger')
            return redirect(url_for('profile.edit_profile'))

        # Обновляем только разрешенные поля
        current_user.username = form.username.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        
        db.session.commit()
        flash('Профиль успешно обновлен.', 'success')
        return redirect(url_for('profile.index'))

    # Заполняем форму текущими данными
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone  # Оставляем если есть в модели

    return render_template('profile/edit.html', form=form)

@profile.route('/profile/deposit', methods=['GET', 'POST'])
@limiter.limit("25 per minute")
@login_required
def deposit():
    """Страница пополнения баланса."""
    try:
        form = BalanceOperationForm()
        quiz_id = request.args.get('quiz_id', type=int)
        quiz = None
        
        if quiz_id:
            quiz = QuizSession.query.get(quiz_id)
            if quiz and quiz.status == 'active':
                form.amount.data = quiz.entry_fee
        
        return render_template('profile/deposit.html', 
                             form=form, 
                             quiz=quiz,
                             user=current_user)
    except Exception as e:
        return handle_error(e)

@profile.route('/profile/withdraw', methods=['GET', 'POST'])
@limiter.limit("25 per minute")
@login_required
def withdraw():
    """Временная заглушка для вывода средств"""
    form = BalanceOperationForm()
    if form.validate_on_submit():
        # Здесь будет интеграция с платежной системой
        flash('Функция вывода средств находится в разработке.', 'info')
        return redirect(url_for('profile.index'))
    return render_template('profile/balance.html', form=form, operation='withdraw')

@profile.route('/process_deposit', methods=['POST'])
@limiter.limit("25 per minute")
@login_required
def process_deposit():
    """Обработка пополнения баланса."""
    try:
        form = BalanceOperationForm()
        if form.validate_on_submit():
            amount = form.amount.data
            
            # Проверка суммы
            if amount < 100:
                flash('Минимальная сумма пополнения - 100₽', 'warning')
                return redirect(url_for('profile.deposit'))
            
            # Обновляем баланс пользователя
            current_user.balance += amount
            db.session.commit()
            
            # Логируем операцию
            log_event(
                action="balance_deposit",
                user_id=current_user.id,
                details=make_details(user_id=current_user.id, ip=request.remote_addr, amount=amount),
                level="INFO",
                message="Пользователь пополнил баланс",
                module=__name__,
                function="process_deposit"
            )
            
            flash(f'Баланс успешно пополнен на {amount}₽', 'success')
            
            # Проверяем, нужно ли перенаправить на страницу квиза
            redirect_to_quiz = request.form.get('redirect_to_quiz', type=int)
            if redirect_to_quiz:
                quiz = QuizSession.query.get(redirect_to_quiz)
                if quiz and quiz.status == 'active':
                    return redirect(url_for('main.index'))
            
            return redirect(url_for('profile.index'))
        else:
            flash('Ошибка в форме. Пожалуйста, проверьте введенные данные.', 'error')
            return redirect(url_for('profile.deposit'))
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при пополнении баланса', 'error')
        return handle_error(e)

@profile.route('/notifications_toggle', methods=['POST'])
@login_required
def toggle_notifications():
    """Включение/отключение уведомлений о квизах (AJAX)."""
    try:
        data = request.get_json()
        if not data or 'enabled' not in data:
            return jsonify({'success': False, 'error': 'Некорректные данные'}), 400

        # CSRF-проверка
        csrf_token = request.headers.get('X-CSRFToken')
        if not csrf_token:
            return jsonify({'success': False, 'error': 'CSRF токен отсутствует'}), 400
        try:
            validate_csrf(csrf_token)
        except Exception:
            return jsonify({'success': False, 'error': 'CSRF токен невалиден'}), 400

        current_user.notifications_enabled = bool(data['enabled'])
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Ошибка сервера'}), 500 