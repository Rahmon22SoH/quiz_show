from flask_mail import Message
from threading import Thread
from flask import render_template, current_app
from app.extensions import mail  # Импортируем только mail из extensions
import os

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    msg = Message(current_app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + subject, sender=current_app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thread = Thread(target=send_async_email, args=(current_app._get_current_object(), msg))
    thread.start()
    return thread
    