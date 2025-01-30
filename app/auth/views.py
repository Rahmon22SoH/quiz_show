# app/auth/views.py

from flask import render_template, flash, redirect, url_for, request, session, abort
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from app.auth import auth
from app.auth.forms import RegistrationForm, LoginForm
from app.auth.auth_utils import log_action
from app.models import User, Role
from app.extensions import db
from app.email import send_email


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():	
        # Проверка уникальности email
        if User.query.filter_by(email=form.email.data).first():
            flash('This email is already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Проверка уникальности username
        if User.query.filter_by(username=form.username.data).first():
            flash('This username is already taken.', 'danger')
            return redirect(url_for('auth.register'))

        # Проверка уникальности телефона
        if form.phone.data and User.query.filter_by(phone=form.phone.data).first():
            flash('This phone number is already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # Назначаем роль по умолчанию ("user")
        default_role = Role.query.filter_by(name='user').first()
        # Создание нового пользователя
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role_id=default_role.id if default_role else None  # Устанавливаем роль по умолчанию
        )
        user.set_password(form.password.data)  # Хеширование пароля
        db.session.add(user)
        db.session.commit()
        print("Transaction committed successfully.")
        # Временные отладочные сообщения
        print(f"Before log_action: user_id={user.id}")
        
        # Логируем регистрацию, передавая ID нового пользователя
        try:
            log_action('Register', details=f"New user: {user.username}, IP: {request.remote_addr}", user_id=user.id)
        except Exception as e:
            print(f"Error in log_action: {e}")
            flash('Failed to log registration.', 'danger')
        # Временные отладочные сообщения
        print("After log_action")

        # Отправка подтверждающего email
        token = user.generate_confirmation_token()  # Метод генерирует токен 
        send_email(user.email, 
            'Confirm Your Account',
            '/mail/confirm', # Шаблон письма
            user=user,
            token=token)
        
        

        flash('На ваш адрес электронной почты было отправлено письмо с подтверждением.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    user = current_user
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        if not user.confirmed:
            flash('Please confirm your account before logging in.', 'warning')
            return redirect(url_for('auth.login'))

        if user.is_locked:
            flash('Your account is locked. Contact support.', 'danger')
            return redirect(url_for('auth.login'))
        
         # Обновляем последние изменения на платформе по пользователю пересмотреть функционал! 
        user.updated_at = datetime.utcnow()
        db.session.commit()

        # Установка сессии
        login_user(user, remember=form.remember_me.data)
        session['current_user'] = user.id

        # Логируем успешный вход
        log_action('Login', details=f"Login user: {user.username},IP: {request.remote_addr}",user_id=user.id)

        flash('Теперь вы вошли в систему.', 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/login.html', form=form)

@auth.route('/logout')
def logout():
    user = current_user
    log_action('Logout', details=f"Logout user: {user.username},IP: {request.remote_addr}",user_id=user.id)
    logout_user()  # Выполняет выход пользователя
    return redirect(url_for('main.index'))  # Перенаправляет на главную страницу

@auth.route('/confirm/<token>')
def confirm_email(token):
    if current_user.is_authenticated and current_user.confirmed:
        flash('Your account is already confirmed.', 'success')
        return redirect(url_for('main.index'))

    user_id = User.verify_confirmation_token(token)
    if not user_id:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))

    if user.confirmed:  # Если уже подтвержден, только обновим время
        flash('Ваш аккаунт уже подтвержден.', 'success')
    else:
        user.confirm()
        db.session.commit()
        # Логируем регистрацию, передавая ID нового пользователя
        flash('Ваша учетная запись подтверждена. Теперь вы можете принять участие в Quiz Jackpot.', 'success')
    
    return redirect(url_for('auth.login'))


# Необходимо проверить, данный функцилнал не тестировался (возоимодействие с send_email)
"""
Проверка времени последней отправки:
Логика проверки времени последней отправки подтверждения через time_since_last_confirmation работает хорошо. Если время с момента последней отправки меньше 1 часа (3600 секунд), пользователю показывается сообщение и повторная отправка не выполняется.
Однако, можно улучшить читаемость кода, вынеся проверку в отдельную переменную:
if current_user.confirmed_at and (datetime.utcnow() - current_user.confirmed_at).total_seconds() < 3600:
    flash('Confirmation email was sent recently. Please wait before requesting again.', 'warning')
    return redirect(url_for('main.index'))
    Безопасность и стабильность:

    Предполагается, что если пользователь не подтвердил email, но прошел менее часа с последней попытки, то ему будет запрещено запрашивать новое письмо.
    Однако если в базе данных нет значения confirmed_at (например, аккаунт только что зарегистрирован), то условие будет корректно работать, и пользователю не будет отказано в запросе на повторную отправку.

Отправка письма:

    Письмо отправляется через send_email. Убедитесь, что функция send_email корректно работает и отправляет подтверждающее письмо с правильным шаблоном. Также стоит убедиться, что путь к шаблону письма ('auth/email/confirm') правильный и файл существует.

Обработка редиректа:

    При успешной отправке нового письма с подтверждением, вы выполняете редирект на главную страницу, что логично для UX.
"""
@auth.route('/resend-confirmation')
def resend_confirmation():
    if current_user.is_authenticated and not current_user.confirmed:
        time_since_last_confirmation = (datetime.utcnow() - current_user.confirmed_at).total_seconds() if current_user.confirmed_at else None
        
        if time_since_last_confirmation and time_since_last_confirmation < 3600:  # 1 час
            flash('Confirmation email was sent recently. Please wait before requesting again.', 'warning')
            return redirect(url_for('main.index'))

        token = current_user.generate_confirmation_token()
        send_email(current_user.email, 'Confirm Your Account', 'auth/email/confirm', user=current_user, token=token)
        flash('A new confirmation email has been sent to your email address.', 'info')
        return redirect(url_for('main.index'))

    return redirect(url_for('auth.login'))
