# Flask Project

## Описание
Flask Project — это веб-приложение-шаблон, разработанное с использованием фреймворка Flask. В проекте реализованы маршруты, работа с базой данных sqllite, отправка писем.

app/ 
	├── main/ 
# Основное приложение │ 
		├── templates/ # HTML-шаблоны │ 
		├── static/ # Статические файлы │ 
		├── init.py # Регистрация Blueprint │ 
		├── views.py # Маршруты │ 
		└── errors.py # Обработчики ошибок 		
	├── email.py # Логика отправки писем 
	├── extensions.py # Регистрация расширений Flask (SQLAlchemy, Migrate и т.д.) 
	├── models.py # SQLAlchemy-модели 
	instance/ # Конфиденциальные данные (файл SQLite) 
	migrations/ # Миграции базы данных 
	config.py # Конфигурация приложения
	hello.py # Точка входа в приложение 
	requirements.txt # Зависимости проекта 
	.env # Переменные окружения (НЕ включать в репозиторий!)

# Установка зависимостей 
pip install -r requirements.txt
pip freeze > requirements.txt - обновление зависимостей 

# Создайте файл .env и добавьте туда переменные окружения:
FLASK_APP=hello.py
FLASK_ENV=development
SECRET_KEY=ваш_секретный_ключ

# Инициализируйте базу данных:
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Запуск приложения 
python .\hello.py
