# api/index.py
from flask import Flask, jsonify

# Vercel ожидает найти переменную 'app'
app = Flask(__name__)

@app.route('/')
def handle_all_requests():
    """Отвечает на любой запрос к приложению."""
    return jsonify({
        "status": "success",
        "message": "Hello, Vercel! Python backend is running.",
        "timestamp": datetime.now().isoformat()
    })

# Импортируем datetime здесь, чтобы он был доступен функции home()
from datetime import datetime 
