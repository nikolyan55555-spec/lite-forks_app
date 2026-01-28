from flask import Flask, request, jsonify, render_template, send_from_directory
from init_data_py import InitData
import jwt
import time
import os

# --- Конфигурация ---
# Используйте переменные окружения Vercel для безопасности
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_FALLBACK_TOKEN")
# BOT_TOKEN = '7729523904:AAEVyCNLL9NXyr_3tJ3TzxUTK94OwJr2GuA'
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "SUPER_SECRET_FALLBACK_KEY")

# Настройка Flask: указываем, где искать статические файлы (в папке static/)
app = Flask(__name__, static_folder='../static')

# --- Утилиты ---
def generate_jwt_token(user_data):
    payload = {
        'user_id': user_data['id'],
        'username': user_data.get('username', 'N/A'),
        'exp': time.time() + 60 * 60 * 24 # Срок действия: 24 часа
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None # Токен истек
    except jwt.InvalidTokenError:
        return None # Неверный токен

# --- Маршруты Flask ---

# 1. Отдача статических файлов (покрывается конфигурацией vercel.json и static_folder)
@app.route('/<path:filename>')
def static_files(filename):
    # Этот маршрут обрабатывает index.html, dashboard.html и любые другие файлы в static/
    return send_from_directory(app.static_folder, filename)

# 2. API-эндпоинт для входа и получения токена (POST запрос из JS)
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    init_data_raw = data.get('initData')

    if not init_data_raw:
        return jsonify({"error": "No initData provided"}), 400

    try:
        # Валидация данных Telegram
        init_data = InitData.parse(init_data_raw)
        init_data.validate(BOT_TOKEN, lifetime=600)
        
        # Генерация JWT токена
        token = generate_jwt_token(init_data.user.to_dict())
        
        return jsonify({"status": "success", "token": token})

    except Exception as e:
        return jsonify({"error": f"Auth failed: {str(e)}"}), 401

# 3. Защищенный API-эндпоинт (требует JWT токен)
@app.route('/api/user_data', methods=['GET'])
def get_user_data_api():
    # Проверяем заголовок авторизации
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized"}), 401
    
    token = auth_header.split("Bearer ")[1]
    user_payload = verify_jwt_token(token)

    if user_payload:
        return jsonify({"status": "success", "user": user_payload})
    else:
        return jsonify({"error": "Invalid or expired token"}), 401

# Обработчик корневого URL, который отдает index.html
@app.route('/')
def index_route():
    return send_from_directory(app.static_folder, 'index.html')

