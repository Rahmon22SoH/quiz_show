# Flask Project

## Описание
Flask Project — это веб-приложение-шаблон, разработанное с использованием фреймворка Flask. В проекте реализованы маршруты, работа с базой данных sqllite, отправка писем.

|flask_project 
├───|app 
│ 	├── templates/
│ 	│   ├── base.html             # Основной шаблон сайта
│ 	│   ├── index.html            # Главная страница
│ 	│   ├── user.html             # Страница пользователя
│ 	│   ├── 404.html              # Страница ошибки 404
│ 	│   ├── 500.html              # Страница ошибки 500
│	│   ├── admin/
│ 	|   |   ├── 404.html          # Страница ошибки 404
│ 	|   |   ├── 500.html          # Страница ошибки 500
│ 	│   │   ├── base.html         # Базовый шаблон админки
│ 	│   │   ├── dashboard.html    # Панель управления
│ 	│   │   ├── logs.html         # Страница логов
│ 	│   │   ├── quizzes.html      # Управление викторинами - квизами
│ 	│   │   ├── users.html        # Управление пользователями
│ 	│   │   └── winners.html      # Страница победителей
│ 	│   │
│ 	│   ├── auth/                 # Шаблоны аутентификации
│ 	│   |   ├── login.html        # Страница входа 
│ 	│   |   ├── register.html     # Страница регистрации 
│ 	|   |   └── telegram_login.html # Страница регистрации telegram
│ 	│   ├── errors/               # Шаблоны c ошибками
│ 	│   |   └── error.html        # Страница c ошибками
│ 	|   ├── macros/
│ 	|   |     └── flash_messages.html # Страница всплывающих сообщений
│ 	│   ├── profile/              # Шаблоны профилем пользователя
│ 	│   │   ├── deposit.html      # Страница 
│ 	│   │   ├── edit.html         # Страница
│ 	│   │   ├── index.html        # Страница профиля
│ 	│   │   └── profile.html
│ 	│   └── quiz/                 # Шаблоны викторин - квизов
│ 	│       └── index.html        # Страница викторин - квизов
│ 	│   
│ 	│  
│ 	├── quiz/
│ 	│   ├── __init__.py           # Инициализация модуля викторин
│ 	│   ├── views.py              # Представления викторин
│ 	│   └── utils.py              # Вспомогательные функции
│ 	│
│ 	├── celery/
│ 	│   ├── __init__.py           # Инициализация Celery
│ 	│   ├── tasks.py              # Задачи Celery
│ 	│   └── beat_schedule.py      # Расписание периодических задач
│ 	│
│ 	├── static/
│ 	│   ├── css/                  # Стили CSS
│ 	│   ├── js/                   # JavaScript файлы
│ 	│   └── images/               # Изображения
│ 	│
│ 	├── admin/
│ 	│   ├── __init__.py           # Инициализация админ-модуля  
│ 	│   └── views.py              # Представления админки 
│ 	│
│ 	├── auth/                     # Шаблоны аутентификации
│ 	│   ├── __init__.py           # Инициализация модуля
│ 	│   ├── views.py              # Представления аутентификации 
│ 	│   ├── session.py            # Управление сессиями пользователей
│ 	│   └── auth_utils.py         # Вспомогательные функции
│ 	│
│ 	├── main/
│ 	│   ├── __init__.py           # Инициализация основного модуля
│ 	│   ├── views.py              # Основные представления 
│ 	│   ├── forms.py              # Основные формы 
│ 	│   └── errors.py             # Обработчики ошибок
│ 	│
│ 	├── models/                   # Модель данных  
│ 	|       ├── __init__.py       # Инициализация основного модуля
│ 	|       ├── base.py           # Базовая модель,наследуются все  модели.
│ 	|       ├── user.py           # Модель Пользователей системы
│ 	│       ├── base.html         # Базовый шаблон админки
│ 	│       ├── role.py           # Модель роли пользователя
│ 	│       ├── log.py            # Модель для логирования действий
│ 	│       ├── quiz_session.py   # Модель сессии квиза
│ 	│       ├── quiz_participant.py # Модель участника квиза
│ 	│       └── quiz_winners.py   # Модель для хранения истории победителей квизов
│ 	│       └── platform_stats.py # Модель для хранения статистики платформы
│ 	│
│ 	│
│ 	├── profile/                  # Создает объект Blueprint
│ 	│   ├── __init__.py           # Инициализация Celery
│ 	│   ├── forms.py       # формы для редактирования профиля,операций с балансом.
│	│   └── views.py              # Содержит маршруты и логику
│	│
│	├── utils/                    # Централизованное управление логированием
│	│   ├── action_logger.py      # Логирование действий пользователей
│	│   ├── error_handlers.py     # Централизованная обработка ошибок
│	│   ├── logger.py             # Настройка логирования для приложения. 
│	│   └── startup.py # Инициализация данных и проверка состояния при старте.
│	│
│	│
│	├── payments/                 # Заглушка на стадии реализации
│	│
│	├── __init__.py               # Инициализация приложения
│	├── debug_celery_worker.py    # Отладка celery
│	├── email.py                  # Логика отправки писем рудимент убрать
│	├── extensions.py  # Регистрация расширений Flask (SQLAlchemy, Migrate и т.д.)
│	├── test_celery_worker.py     # Тест celery
│	├── instance/                 # Конфиденциальные данные (файл SQLite) 
│	├── logs/                     # Логи 
│	├──	migrations/               # Миграции базы данных
│	└── venv/                     # Виртуальное окружение
│	
│	 
│
├── .env                      # Переменные окружения (НЕ включать в репозиторий!)
├── .flaskenv                 # Переменные окружения для Flask
├── .gitignore                # Игнорирование файлов git
├── celery_worker.py 		  # Запуск celery worker
├── config.py                 # Конфигурация приложения
├── error.log                 # Логи
├── hello.py                  # Точка входа в приложение 
├── requirements.txt          # Зависимости проекта 
└── README.md                 # Описание проекта

	
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


# При тестировании и доработки функционала на локальном сервере нужно использовать туннелирование, потому что Telegram и платежные терминалы требует публично доступный URL.
# Запуск и настройка тунелирования через LocalTunnel
	Скачайте Node.js для Windows:
	Перейдите на https://nodejs.org/
	Скачайте LTS (Long Term Support) версию
	Установите, следуя инструкциям установщика
	Важно: Перезагрузите компьютер после установки
  После перезагрузки:
  - npm install -g localtunnel выполнить единожды 
  - Запускаем придлжения python .\hello.py
  - Запустите туннель с фиксированным доменом: lt --port 5000 --subdomain quizz-show-app
  - После запуска вы увидите сообщение вида: your url is: https://quizz-show-app.loca.lt

# Запуск приложения 
python .\hello.py

# Структура запуска:
Redis сервер - обработка очередей - пока запускаем в докер файл 

Celery worker - выполнение задач - celery -A celery_worker.celery worker --pool=solo -l info
Celery beat - планировщик периодических задач - celery -A celery_worker.celery beat -l info
Flask приложение - веб-интерфейс - python .\hello.py

Если возникнет ошибка с --pool=solo, попробуйте без этого параметра:
celery -A celery_worker.celery worker -l info
также можно использовать флаг -P:
celery -A celery_worker.celery worker -P solo -l info

# Структура запуска browser-tools-server (помошь в логах с консолью браузера )
1. обновить в cursor ai server не закрывая консоль
2. запустить npx @agentdeskai/browser-tools-server@1.2.0 (npx @agentdeskai/browser-tools-server@1.2.0)


# Запуск нагрузочного тестирования 
locust -f locustfile.py на странице http://localhost:8089/
python generate_test_data.py - генерируем тестовые данные 

## Правки перед продакшеном 
__init__.py в файле 
from app.extensions import db, login_manager, mail, moment, bootstrap, migrate, cache, csrf # (Убрать функ после тестов csrf)
# SESSION_COOKIE_SECURE=True, # <-- Закомментировано, берем из config.py (разкоментировать)
# REMEMBER_COOKIE_SECURE=True, # <-- Закомментировано, берем из config.py (разкоментировать)
# Настройка CORS для localtunnel нужно будет на URL ? 

config.py
SESSION_COOKIE_SECURE = False # Поменять на  True после тестов на нагрузку 
REMEMBER_COOKIE_SECURE = False # Поменять на  True после тестов на нагрузку 

C:\Users\Роман\Desktop\flask_project\app\auth\views.py
# --- Маршрут ТОЛЬКО для тестов Locust --- НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ без защиты! УБРАТЬ ДЛЯ ТЕСТОВ

@auth.route('/_locust_login_', methods=['POST']) - удалить 
from ..extensions import csrf # <--- Импортируем из extensions --- НЕ ИСПОЛЬЗОВАТЬ В ПРОДАКШЕНЕ без защиты УБРАТЬ ДЛЯ ТЕСТОВ 

extensions.py
from flask_wtf.csrf import CSRFProtect # (Убрать после тестов CSRFProtect)
csrf = CSRFProtect() # (Убрать после тестов CSRFProtect) 

Подготовка к продакшену 
1.Для реального продакшена — используйте Gunicorn или uWSGI с несколькими воркерами и за nginx.
2.Если нужно больше RPS — увеличьте количество воркеров и потоков, настройте connection pooling для БД.
3. Для тестов кэша — можно временно увеличить timeout, чтобы явно видеть эффект кэширования.
4. Мониторинг — подключите APM (например, Sentry, NewRelic, Datadog) для отслеживания производительности в реальном времени.

# Docker работа в контейнере 
Пересобери образ web-контейнера docker-compose build web
Перезапусти контейнеры - docker-compose up -d
Проверь статус контейнеров - docker ps
Проверь логи web-контейнера в реальном времени - docker logs -f web
После запуска контейнера с приложением, выполнить команду: docker exec -it flask_project-web-1
мониторинг - docker stats flask_project-web-1 flask_project-redis-1 flask_project-db-1
Проверь статус контейнеров - docker ps
слип контейнер - docker-compose run --rm web sleep infinity
запуск в контейнере файлов docker exec -it flask_project-web-1 python generate_test_data.py
Припервом запуске контейнера нужно будет выполнить команду: потушить апп в слип и сделать миграцию и установку БД.
Далее необходимо вставить данные в таблицу roles:
INSERT INTO roles (name, id, created_at, updated_at)
VALUES
  ('admin', 1, NOW(), NOW()),
  ('user', 2, NOW(), NOW());