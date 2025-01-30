from flask import render_template, request
from app.models import User, Log
from app.admin import admin
from app.extensions import db
from app.auth.auth_utils import admin_required

@admin.route('/')
@admin_required
def dashboard():
    """Главная страница админ-панели с меню."""
    return render_template('admin/dashboard.html')

@admin.route('/users')
@admin_required
def view_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

#Перенесем в отдельный модуль =================
@admin.route('/quizzes')
@admin_required
def view_quizzes():
    return render_template('admin/quizzes.html')


@admin.route('/logs')
@admin_required
def view_logs():
    # Получаем номер текущей страницы из параметров URL, по умолчанию 1
    page = request.args.get('page', 1, type=int)
    # Запрос с использованием пагинации
    per_page = 20  # Количество записей на странице
    pagination = Log.query.order_by(Log.timestamp.desc()).paginate(page=page, per_page=per_page)

    logs = pagination.items  # Логи для текущей страницы
    return render_template('admin/logs.html', logs=logs, pagination=pagination)
