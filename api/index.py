# api/index.py
import time
import hashlib
import hmac
from urllib.parse import parse_qs
from flask import Flask, request, render_template_string

# Vercel ожидает найти переменную 'app'
app = Flask(__name__)

# --- ЗАГЛУШКИ ДЛЯ ПРИМЕРА (ЗАМЕНИТЕ НА ВАШУ РЕАЛИЗАЦИЮ) ---
BOT_TOKEN = "8385615154:AAEwVHr3LcUVkDAL5NiJSImOy2trol_YRp0" 
USERS_DATA = {
    # Пример данных пользователя: {user_id: {'is_subscribed': True/False}}
    12345678: {'is_subscribed': True} 
}

def verify_telegram_signature(data):
    """(Заглушка) Реализуйте здесь вашу функцию верификации из предыдущего ответа."""
    # Ваша реальная функция проверки хэша здесь
    return True # В тестовых целях пока вернем True

def create_service_html(is_subscribed):
    """(Заглушка) Генерирует HTML в зависимости от подписки."""
    if is_subscribed:
        return "<h1>Добро пожаловать, подписчик!</h1><p>Ваш секретный контент здесь.</p>"
    else:
        return "<h1>Вы не подписаны</h1><p>Пожалуйста, подпишитесь на канал, чтобы увидеть контент.</p>"
# --- КОНЕЦ ЗАГЛУШЕК ---


@app.route('/')
def handle_all_requests():
    """
    Основная функция Vercel. 
    Получает запрос, проверяет параметры URL, генерирует и возвращает полный HTML.
    """
    is_authorized = False
    is_subscribed = False
    result_html = "" 

    # 1. Извлекаем параметры из URL-строки запроса
    query_string = request.query_string.decode('utf-8')
    # request.args в Flask уже парсит query_string, parse_qs не нужен
    auth_data = request.args 

    print(auth_data) # Отладочный вывод в логи Vercel

    # 2. Проверяем авторизацию Telegram
    if auth_data.get('id') and auth_data.get('hash'):
        if verify_telegram_signature(auth_data):
            # Проверяем срок годности данных
            # Flask request.args возвращает строки, нужно преобразовать в int
            auth_date = int(auth_data.get('auth_date', 0)) 
            
            # Проверка актуальности данных (86400 секунд = 24 часа)
            if time.time() - auth_date <= 86400:
                is_authorized = True
                user_id = int(auth_data.get('id'))
                user_info = USERS_DATA.get(user_id)
                if user_info and user_info['is_subscribed']:
                    is_subscribed = True
                
                # 3. Генерируем контент, соответствующий статусу подписки
                result_html = create_service_html(is_subscribed=is_subscribed)
            else:
                result_html = "<p>Ошибка: Срок действия данных Telegram истек.</p>"
        else:
            result_html = "<p>Ошибка: Неверная подпись Telegram.</p>"
    else:
        result_html = "<p>Ошибка: Нет данных авторизации Telegram.</p>"
    
    # Flask имеет встроенную функцию render_template_string
    return render_template_string(result_html)
