from locust import HttpUser, task, between, SequentialTaskSet
import logging # Для отладки
import time
import random
import re
from datetime import datetime
from bs4 import BeautifulSoup
import itertools # Добавляем импорт

# Настройка логирования с более подробной информацией
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Счетчик для уникальных номеров пользователей
user_number = itertools.count(0)

# -- Вспомогательная функция для извлечения CSRF --
def extract_csrf_from_html(html_content):
    """Извлекает CSRF-токен из HTML, ищет его в мета-теге."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Ищем токен в мета-теге <meta name="csrf-token" content="...">
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if csrf_meta and csrf_meta.has_attr('content'):
            token = csrf_meta['content']
            logger.debug(f"CSRF token found in meta tag: {token[:10]}...")
            return token
        logger.warning("CSRF token not found in meta tag (name='csrf-token').")
    except Exception as e:
        logger.error(f"Error parsing HTML for CSRF meta tag: {e}")
    return None

class UserScenario(SequentialTaskSet):
    """Последовательность действий пользователя."""
    
    csrf_token = None
    quizzes_to_join = [] # Список квизов для присоединения: [{'id': ..., 'amount': ...}]
    joined_quiz_ids = [] # Список ID квизов, к которым успешно присоединились
    user_id = -1 # Добавляем атрибут для хранения номера пользователя

    def on_start(self):
        """Выполняется один раз при старте TaskSet.
        1. Логин.
        2. Получение списка квизов через тестовый API.
        3. CSRF токен будет получен позже из ответа /index.
        """
        self.csrf_token = None # Сбрасываем токен
        self.quizzes_to_join = []
        self.joined_quiz_ids = []
        login_successful = False
        
        # Получаем уникальный номер для этого виртуального пользователя
        raw_user_id = next(user_number)
        total_test_users = 100 # Укажите здесь точное количество созданных тестовых пользователей (0-99)
        self.user_id = raw_user_id % total_test_users # ID будет циклически меняться от 0 до 99
        username = f"testuser{self.user_id}"
        logger.info(f"[User {self.user_id}] Starting scenario as {username}")

        # 1. Логин под уникальным именем
        payload = {"username": username} # Используем уникальное имя
        with self.client.post("/auth/_locust_login_", json=payload, catch_response=True, name="[01_Auth] Test Login") as response:
            if response.status_code == 200 and response.json().get("status") == "ok":
                login_successful = True
                logger.info(f"[User {self.user_id}] Login successful as {username}.")
            else:
                # Логируем ошибку с указанием пользователя
                logger.error(f"[User {self.user_id}] Login failed for {username}: {response.text}")
                response.failure(f"Login failed for {username}: {response.text}")
                self.interrupt()
                return
        
        # 2. Получение списка квизов через тестовый API
        test_api_url = "/quiz/_test/active_quizzes" 
        with self.client.get(test_api_url, catch_response=True, name="[02_Setup] Get Active Quizzes (Test API)") as quiz_response:
            if quiz_response.status_code == 200:
                try:
                    self.quizzes_to_join = quiz_response.json()
                    if not isinstance(self.quizzes_to_join, list): # Доп. проверка типа
                        logger.error(f"[User {self.user_id}] Invalid data type received from {test_api_url}.")
                        self.quizzes_to_join = [] # Reset list
                        quiz_response.failure("Invalid data type for quiz list")
                    else:
                        logger.info(f"[User {self.user_id}] Received {len(self.quizzes_to_join)} quizzes: {[q.get('id', 'N/A') for q in self.quizzes_to_join]}")
                except ValueError:
                    logger.error(f"[User {self.user_id}] Failed to parse quiz list JSON.")
                    self.quizzes_to_join = [] # Reset list
                    quiz_response.failure("Invalid JSON for quiz list")
                except Exception as e: # Ловим другие возможные ошибки парсинга
                    logger.error(f"[User {self.user_id}] Error processing quiz list response: {e}")
                    self.quizzes_to_join = [] # Reset list
                    quiz_response.failure("Error processing quiz list")
            elif quiz_response.status_code == 404:
                 logger.error(f"[User {self.user_id}] Failed to get quiz list: 404 on {test_api_url}.")
                 quiz_response.failure(f"Failed to get quiz list: 404 on {test_api_url}")
            else:
                 logger.error(f"[User {self.user_id}] Failed to get quiz list: {quiz_response.status_code}")
                 quiz_response.failure(f"Failed to get quiz list: {quiz_response.status_code}")
        
        # 3. Не получаем CSRF здесь, получим его в view_cached_quiz_page_task

    @task
    def view_main_index_task(self):
        """Задача: Просмотр главной страницы /index."""
        logger.debug(f"[User {self.user_id}] Executing view_main_index_task")
        with self.client.get("/index", catch_response=True, name="[Main] View Index Page") as response:
            if response.status_code == 200:
                response.success()
                logger.debug(f"[User {self.user_id}] Successfully loaded /index.")
            else:
                logger.error(f"[User {self.user_id}] Failed to load /index: {response.status_code}")
                response.failure(f"Failed index page load: {response.status_code}")

    @task
    def get_csrf_from_profile_task(self):
        """Задача: Получение CSRF токена со страницы профиля /profile/index/."""
        logger.debug(f"[User {self.user_id}] Executing get_csrf_from_profile_task")
        with self.client.get("/profile/index/", catch_response=True, name="[Profile] Get CSRF Token") as response:
            if response.status_code == 200:
                response.success()
                new_csrf = extract_csrf_from_html(response.text)
                if new_csrf:
                    self.csrf_token = new_csrf
                    logger.info(f"[User {self.user_id}][get_csrf_from_profile] Refreshed CSRF: {self.csrf_token[:10]}...")
                else:
                    logger.warning(f"[User {self.user_id}][get_csrf_from_profile] Could not extract CSRF.")
                    self.csrf_token = None # Reset token if not found
            else:
                logger.error(f"[User {self.user_id}][get_csrf_from_profile] Failed: {response.status_code}")
                response.failure(f"Failed profile page CSRF: {response.status_code}")
                self.csrf_token = None # Reset token on failure

    @task
    def view_cached_quiz_page_task(self):
        """Задача: Просмотр КЭШИРОВАННОЙ страницы квизов /quiz/."""
        logger.debug(f"[User {self.user_id}] Executing view_cached_quiz_page_task")
        with self.client.get("/quiz/", catch_response=True, name="[Quiz] View Cached Quiz Page") as response:
              if response.status_code == 200:
                  response.success()
                  logger.debug(f"[User {self.user_id}][view_cached_quiz_page] Loaded /quiz/.")
              else:
                  logger.error(f"[User {self.user_id}][view_cached_quiz_page] Failed: {response.status_code}")
                  response.failure(f"Failed quiz page load: {response.status_code}")

    @task
    def join_next_quiz_task(self):
        """Задача: Присоединение к СЛЕДУЮЩЕМУ квизу из списка."""
        logger.debug(f"[User {self.user_id}] Executing join_next_quiz_task")
        if not self.quizzes_to_join:
            logger.info(f"[User {self.user_id}][join_next_quiz] No more quizzes. Skipping.")
            return
            
        if not self.csrf_token:
            logger.error(f"[User {self.user_id}][join_next_quiz] No CSRF token. Skipping.")
            return
            
        quiz_to_join = self.quizzes_to_join[0]
        quiz_id = quiz_to_join.get('id')
        amount = quiz_to_join.get('amount')

        if quiz_id is None or amount is None:
             logger.error(f"[User {self.user_id}][join_next_quiz] Invalid quiz data: {quiz_to_join}. Skipping.")
             self.quizzes_to_join.pop(0)
             return
            
        logger.info(f"[User {self.user_id}][join_next_quiz] Attempting quiz {quiz_id} (Amount: {amount})")
        form_data = {"csrf_token": self.csrf_token, "amount": amount}

        with self.client.post(f"/quiz/join/{quiz_id}", data=form_data, name="[Quiz] Join Next Quiz", catch_response=True) as response:
            response_text = response.text.lower() if response.text else ""
            processed = False

            if response.status_code in [200, 302, 303]:
                if "уже участвуете" in response_text or "already joined" in response_text:
                    logger.info(f"[User {self.user_id}][join_next_quiz] Already joined quiz {quiz_id}.")
                    self.joined_quiz_ids.append(quiz_id)
                    processed = True
                    response.success()
                elif "недостаточно средств" in response_text:
                    logger.info(f"[User {self.user_id}][join_next_quiz] Insufficient funds for quiz {quiz_id}. Amount: {amount}")
                    processed = True
                    response.success()
                elif "успешно присоединились" in response_text or "successfully joined" in response_text:
                     logger.info(f"[User {self.user_id}][join_next_quiz] Successfully joined quiz {quiz_id}.")
                     self.joined_quiz_ids.append(quiz_id)
                     processed = True
                     response.success()
                else:
                     logger.warning(f"[User {self.user_id}][join_next_quiz] Joined quiz {quiz_id} ({response.status_code}) but unexpected response: {response.text[:100]}...")
                     self.joined_quiz_ids.append(quiz_id)
                     processed = True
                     response.success()

            elif response.status_code == 400:
                if "csrf" in response_text and "token" in response_text:
                     logger.error(f"[User {self.user_id}][join_next_quiz] Failed (400 CSRF) for quiz {quiz_id}. Response: {response.text}")
                     response.failure("Join Failed (400 CSRF)")
                     self.csrf_token = None
                     return
                else:
                     logger.error(f"[User {self.user_id}][join_next_quiz] Failed (400 Other) for quiz {quiz_id}. Response: {response.text}")
                     response.failure("Join Failed (400 Other)")
                     return
            
            elif response.status_code == 402:
                 logger.info(f"[User {self.user_id}][join_next_quiz] Insufficient funds (402) for quiz {quiz_id}. Amount: {amount}")
                 processed = True
                 response.success()

            elif response.status_code == 404:
                 logger.warning(f"[User {self.user_id}][join_next_quiz] Quiz {quiz_id} not found (404).")
                 processed = True
                 response.failure("Join Failed (404 Quiz Not Found)")

            elif response.status_code == 409:
                 logger.info(f"[User {self.user_id}][join_next_quiz] Conflict (409) for quiz {quiz_id}.")
                 self.joined_quiz_ids.append(quiz_id)
                 processed = True
                 response.success()

            else:
                logger.error(f"[User {self.user_id}][join_next_quiz] Failed ({response.status_code}) for quiz {quiz_id}. Response: {response.text}")
                response.failure(f"Join Failed ({response.status_code})")
                return

            if processed:
                try:
                    removed_quiz = self.quizzes_to_join.pop(0)
                    logger.info(f"[User {self.user_id}][join_next_quiz] Quiz {removed_quiz.get('id')} processed. Remaining: {len(self.quizzes_to_join)}")
                except IndexError:
                     logger.error(f"[User {self.user_id}][join_next_quiz] Tried to pop from empty list.")

    @task
    def view_profile_page_task(self):
        """Задача: Просмотр профиля пользователя ПОСЛЕ квизов."""
        logger.debug(f"[User {self.user_id}] Executing view_profile_page_task (final)")
        if self.quizzes_to_join:
             logger.debug(f"[User {self.user_id}][view_profile_page] Still quizzes to join, skipping final profile view.")
             return
            
        logger.info(f"[User {self.user_id}][view_profile_page] All quizzes processed, viewing profile.")
        with self.client.get("/profile/index/", catch_response=True, name="[Profile] View Profile Page (Final)") as response:
            if response.status_code == 200:
                response.success()
                logger.debug(f"[User {self.user_id}][view_profile_page] Final profile view successful.")
            else:
                 logger.error(f"[User {self.user_id}][view_profile_page] Final profile view failed: {response.status_code}")
                 response.failure(f"Failed final profile view: {response.status_code}")

        logger.info(f"[User {self.user_id}][view_profile_page] User finished scenario. Stopping.")
        self.interrupt()

class QuizUser(HttpUser):
    """Основной класс пользователя Locust."""
    wait_time = between(2, 5) # Можно немного уменьшить ожидание
    host = "http://127.0.0.1:5000" # Укажите ваш хост
    tasks = [UserScenario] # Запускаем последовательность задач

    # Убираем старые атрибуты, т.к. они теперь в TaskSet
    # csrf_token = None
    # login_successful = False 
    # available_quizzes = []
    # joined_quiz_ids = []
    
    # Можно оставить глобальные счетчики, если нужно
    # total_response_time = 0 
    # ... и т.д.