import smtplib
import logging

# Включаем логирование для более детальной отладки
logging.basicConfig(level=logging.DEBUG)

SMTP_SERVER = 'smtp.gmail.com'  # Или другой SMTP-сервер
SMTP_PORT = 587   
EMAIL = 'mebelnazakazms@gmail.com'
PASSWORD = 'vkao iumw tkbv lcsu'
RECIPIENT = 'mebelnazakazms@gmail.com'

try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.set_debuglevel(1)  # Уровень отладки для SMTP
        server.ehlo()  # Приветствие сервера
        server.starttls()  # Начинаем TLS-сессию
        server.login(EMAIL, PASSWORD)  # Логинимся
        message = """\
Subject: Test Email from Debug
This is a test email sent with debug enabled."""
        server.sendmail(EMAIL, RECIPIENT, message)  # Отправляем письмо
        print("Email sent successfully.")
except smtplib.SMTPException as e:
    print(f"SMTP error occurred: {e}")
except Exception as e:
    print(f"General error occurred: {e}")