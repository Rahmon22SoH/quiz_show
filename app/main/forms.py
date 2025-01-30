from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp


class NameForm(FlaskForm):
    # name = StringField('Your name', validators=[DataRequired()])
    # submit = SubmitField('Submit')
    pass