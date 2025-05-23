from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length

class ProfileEditForm(FlaskForm):
    """Форма редактирования профиля пользователя"""
    username = StringField('Имя пользователя', validators=[
        DataRequired(message="Это поле обязательно"),
        Length(min=2, max=64, message="Имя пользователя должно быть от 2 до 64 символов")
    ])
    
    first_name = StringField('Имя', render_kw={'readonly': True})
    
    last_name = StringField('Фамилия', render_kw={'readonly': True})
    
    # Телефон только для отображения, изменить нельзя
    phone = StringField('Телефон', render_kw={'readonly': True})
    
    submit = SubmitField('Сохранить изменения')

class BalanceOperationForm(FlaskForm):
    """Форма для операций с балансом (временная заглушка)"""
    amount = FloatField('Сумма', validators=[
        DataRequired(message="Введите сумму")
    ])
    submit = SubmitField('Подтвердить') 