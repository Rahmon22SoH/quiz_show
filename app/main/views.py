from flask import render_template, session, redirect, url_for, current_app
from flask_login import current_user, login_user, logout_user
from datetime import datetime, timezone
from app.main import main
from app.models import User
from app.extensions import db
from app.email import send_email
from app.main.forms import NameForm



@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit() and current_user.is_authenticated:
        # Обновляем дату последнего визита данный функционал не релизован нет обработки в User Поля last_seen у модели User в данном коде нет. Если оно должно быть реализовано, нужно добавить его в модель пользователя (User) и инициализировать в базе данных.
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('main.index'))
    
    # Рендерим шаблон и передаем имя пользователя или "Guest", если не аутентифицирован

    return render_template('index.html', 
                       form=form, 
                       name=getattr(current_user, 'username', 'Guest'), 
                       current_time=datetime.now(timezone.utc))