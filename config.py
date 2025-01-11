from dotenv import load_dotenv
import os
basedir = os.path.abspath(os.path.dirname(__file__))
# Загружаем переменные окружения из файла .env
load_dotenv()

class Config:
	# Здесь настраиваем параметры для отправки писем через SMTP-сервер Google
	MAIL_SERVER  = 'smtp.gmail.com'
	MAIL_PORT = 587
	MAIL_USE_TLS= True
	MAIL_USERNAME = os.getenv('MAIL_USERNAME')
	MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
	FLASKY_MAIL_SUBJECT_PREFIX  = '[Flasky]'
	FLASKY_MAIL_SENDER  = 'Flasky Admin <mebelnazakazms@gmail.com>'
	FLASKY_ADMIN  = os.getenv('FLASKY_ADMIN')
	SQLALCHEMY_DATABASE_URI='sqlite:///data.sqlite'
	SQLALCHEMY_COMMIT_ON_TEARDOWN = True
	SECRET_KEY= 'mysecretkey'