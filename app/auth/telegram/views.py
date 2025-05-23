from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, current_user, login_required
from . import telegram_auth
from app.models import User, Log
from app.extensions import db
from ...auth.telegram.utils import verify_telegram_data
import json
from app.utils.logger import log_event

@telegram_auth.route('/login')
def login():
    """Страница с Telegram Login Widget."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('auth/telegram_login.html')

@telegram_auth.route('/callback', methods=['GET', 'POST'])
def callback():
    """Обработчик callback от Telegram Login Widget."""
    try:
        # Получаем данные от Telegram
        if request.method == 'POST':
            auth_data = request.form.to_dict()
        else:
            auth_data = request.args.to_dict()

        # Логируем полученные данные (для отладки)
        current_app.logger.info(f"Received Telegram auth data: {json.dumps(auth_data)}")
        
        # Проверяем подпись данных
        if not verify_telegram_data(auth_data):
            current_app.logger.warning("Invalid Telegram data signature")
            flash('Ошибка аутентификации через Telegram: неверная подпись данных.', 'danger')
            return redirect(url_for('auth.login'))
        
        try:
            # Ищем или создаем пользователя
            user = User.get_or_create_from_telegram(auth_data)
            
            # Создаем запись в логах
            log = Log(
                user_id=user.id,
                action='telegram_login',
                details=f"Telegram ID: {auth_data.get('id')}"
            )
            if not log.save():
                raise Exception("Failed to save log entry")
            
            # Входим пользователя в систему
            login_user(user)
            
            log_event(
                action="login_success",
                user_id=user.id,
                details=f"Telegram ID: {auth_data.get('id')}, IP: {request.remote_addr}",
                level="INFO",
                message="Пользователь успешно вошёл через Telegram",
                module=__name__,
                function="callback"
            )
            
            flash(f'Добро пожаловать, {user.first_name}!', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            current_app.logger.error(f"Error processing Telegram user: {str(e)}")
            db.session.rollback()
            log_event(
                action="login_failed",
                user_id=None,
                details=f"Ошибка входа через Telegram: {str(e)}, IP: {request.remote_addr}",
                level="WARNING",
                message="Ошибка входа через Telegram",
                module=__name__,
                function="callback"
            )
            flash('Произошла ошибка при обработке данных пользователя.', 'danger')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        current_app.logger.error(f"Telegram auth error: {str(e)}")
        log_event(
            action="login_failed",
            user_id=None,
            details=f"Ошибка входа через Telegram: {str(e)}, IP: {request.remote_addr}",
            level="WARNING",
            message="Ошибка входа через Telegram",
            module=__name__,
            function="callback"
        )
        flash('Произошла ошибка при входе через Telegram.', 'danger')
        return redirect(url_for('auth.login'))

@telegram_auth.route('/status')
@login_required
def auth_status():
    """Проверка статуса аутентификации."""
    return jsonify({
        'authenticated': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'telegram_id': current_user.telegram_id,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'photo_url': current_user.telegram_photo_url
        }
    }) 