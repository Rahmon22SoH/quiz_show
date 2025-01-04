from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from datetime import datetime, timezone
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
moment = Moment(app)
bootstrap = Bootstrap(app)
app.config['SECRET_KEY'] = 'mysecretkey'



@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods = ['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        old_name = session.get('name')
        if old_name is not None and form.name.data:
            flash(f'Похоже вы сменили имя ваше старое имя {old_name}.')  # выводим предыдущее имя в случае изменения имени
        session['name'] = form.name.data # значение, введённое пользователем в это поле.
        form.name.data = ''  # очищаем поле ввода после отправки
        return redirect(url_for('index')) # Убераем повторную отправку формы GET запросом     
    return render_template('index.html', form=form, name=session.get('name'),  current_time=datetime.now(timezone.utc)) 
"""
session - сохраняем данные в запрсе пользователя
функция url_for() - генерирует url на основе карты адресов
"""

@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)

class NameForm(FlaskForm):
    name = StringField('Your name', validators=[DataRequired()]) # required гарантируем что не можем отправить пустое поле 
    submit = SubmitField('Submit')
    
if __name__ == '__main__':
	app.run(debug=True, port=8080)