# wsgi.py - точка входа для Beget

import sys
import os

# Добавляем корневую директорию проекта в пути Python
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Импортируем объект 'app' из вашего файла app.py
from app import app as application
