from typing import Dict
import textwrap
from datetime import datetime
import os
import base64
from datetime import datetime
import logging
import yaml
import random
import time

from urllib.parse import urlparse
import requests
from flask import (
    Flask, render_template, redirect, url_for, flash, session, render_template_string
)
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
from functools import wraps


logging.basicConfig(
    level=logging.INFO,   
    format='[%(name)s] %(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger('FlaskAPP')

try:
    with open('/home/ndubrovnyi/BettingForks/conf/config.yml', encoding='utf-8') as f:
        CONFIG_DATA = yaml.safe_load(f)
except:
    with open('static/config.yml', encoding='utf-8') as f:
        CONFIG_DATA = yaml.safe_load(f)


SECRET_APP_KEY = os.environ.get("SECRET_APP_KEY")
if not SECRET_APP_KEY:
    SECRET_APP_KEY = CONFIG_DATA.get('secret_app_token')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_APP_KEY
app.config['SESSION_PROTECTION'] = 'strong'

GITHUB_OWNER = 'nikolyan55555-spec'
GITHUB_REPO = 'lite-forks_storage'
USERS_FILE_PATH = 'users.json'
DATA_FILE_PATH = 'forks.json'
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    GITHUB_TOKEN = CONFIG_DATA.get('git_token')


SPORTS_MAPPER = {
    'football': {
        'name': 'Футбол',
        'icon': "⚽",
        'color': "#f2e3bf"
    }
}
SPORTNAME_MAPPER = {
    sport_info['name']: sport_name for sport_name, sport_info in SPORTS_MAPPER.items()
}
NOMINAL_VALUE = 1000
FREE_PER_LIMIT = 2

LOGO_PATH = 'static/logo.png'
try:
    with open(LOGO_PATH, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode("utf-8")
        # Формируем data URL:
        LOGO_SRC = f"data:image/png;base64,{logo_data}"
except FileNotFoundError:
    LOGO_SRC = ""
    print("Error: logo.png not found for Base64 encoding.")

BOOKS_MAIN_URLS = {
    sport_name: {
        book_name: book_info.get('main_url') 
        for book_name, book_info in sport_info['bookmakers'].items()
    } for sport_name, sport_info in CONFIG_DATA['pipeline_config'].items()
}
UTM_SOURCES = ['tg_bot', 'messenger', 'external_share', 'chat_link']

def get_json_data_from_git(path: str) -> Dict:

    repo_api = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/branches/main"
    branch_info = requests.get(
        url=repo_api,
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
    ).json()
    last_sha = branch_info['commit']['sha']
    
    api_url = f'https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{last_sha}/{path}'
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
    }

    try:
        response = requests.get(
            url=api_url,
            headers=headers
        )
        return response.json()
    except Exception as e:
        return {}
    

def generate_fork_block_html(fork_data, include_event_link=False):
    event_time_fmt = datetime.strptime(fork_data['event_time'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    created_time_fmt = datetime.fromisoformat(fork_data['created_time']).strftime('%d.%m.%Y %H:%M')
    bet_rows_html = ""
    for i in range(len(fork_data['bets_names'])):
        base_url = BOOKS_MAIN_URLS.get(SPORTNAME_MAPPER.get(fork_data['sport_name']), {}).get(fork_data['bookmakers'][i], "")
        event_url = fork_data['events_urls'][i]
        event_url = f"{event_url}?from={random.choice(UTM_SOURCES)}&ref=share" 
        bk_domain = urlparse(base_url).netloc if base_url else "букмекера"
        if base_url:
            link_html = f'''<a href="#" onclick="finalSafeJump('{event_url}', '{base_url}', '{bk_domain}'); return false;">🔗 Перейти</a>'''
        else:
            link_html = f'<a href="{event_url}" target="_blank" rel="noreferrer" class="jump-link">🔗 Перейти</a>'
        bet_rows_html += textwrap.dedent(f"""
        <tr class="bet-row">
            <td>{fork_data['bets_names'][i]}</td>
            <td>{fork_data['bets_values'][i]}</td>
            <td>{(fork_data['values'][i]/NOMINAL_VALUE * 100):.2f} %</td>
            <td>{fork_data['bookmakers'][i]}</td>
            <td>{link_html}</td>
        </tr>
        """)
    teams_display = f"{fork_data['team_1']} vs {fork_data['team_2']}"
    if include_event_link:
        teams_display = f'<a href="#" onclick="showPage(\'{fork_data["event_id"]}\'); return false;">{teams_display}</a>'

    return textwrap.dedent(f"""
    <table class="forks-table">
        <!-- Группа столбцов с фиксированной шириной для выравнивания всех блоков -->
        <colgroup>
            <col style="width: 40%;"> <!-- Название ставки -->
            <col style="width: 10%;"> <!-- Кэф -->
            <col style="width: 15%;"> <!-- Сумма ставки -->
            <col style="width: 20%;"> <!-- Букмекер -->
            <col style="width: 15%;"> <!-- Ссылка -->
        </colgroup>
        <tbody class="fork-block">
            <tr class="fork-header-row" style="background-color: {fork_data['sport_color']};">
                <td colspan="5">
                    <span class="sport-icon">{fork_data['sport_icon']}</span>
                    <span class="sport-type">{fork_data['sport_name']}.</span>
                    <span style="margin-left: 5px; font-weight: normal;">{fork_data['competition_name']}</span>
                </td>
            </tr>
            <tr class="event-info-row"><td colspan="2"><strong>Событие:</strong> {teams_display}</td><td><strong>Прибыль:</strong> <span class="profit-value">{(100*(fork_data['profit']-NOMINAL_VALUE)/NOMINAL_VALUE):.2f}%</span></td><td><strong>Начало:</strong> {event_time_fmt}</td><td><strong>Создано:</strong> {created_time_fmt}</td></tr>
            <tr class="bets-header-row"><th>Название ставки</th><th>Кэф.</th><th>Сумма ставки</th><th>Букмекер</th><th>Ссылка</th></tr>
            {bet_rows_html}
        </tbody>
    </table>
    """)


def create_service_html(forks_data: Dict, is_subscribed: bool, user_id: str):

    RAW_FORKS_LIST = []
    for sport_name, fork_list in forks_data.items():
        for fork in fork_list:
            fork['sport_name'] = sport_name
        RAW_FORKS_LIST.extend(fork_list)

    RAW_FORKS_LIST = sorted(RAW_FORKS_LIST, key=lambda x: x['profit'], reverse=True)
    FREE_RAW_FORKS_LIST = [
        fork for fork in RAW_FORKS_LIST 
        if (100*(fork['profit']-NOMINAL_VALUE)/NOMINAL_VALUE) <= FREE_PER_LIMIT
    ]
    all_forks_count = len(RAW_FORKS_LIST)
    free_forks_count = len(FREE_RAW_FORKS_LIST)
    paid_forks_count = all_forks_count - free_forks_count

    free_text = f"""Найдено: {all_forks_count} вилок \n
    С прибылью более {FREE_PER_LIMIT}: {paid_forks_count} вилок
    С прибылью до {FREE_PER_LIMIT}: {free_forks_count} вилок
    Чтобы получать вилки с прибылью более {FREE_PER_LIMIT} необходима премиум подписка.
    Оформить подписку можно через Telegram
    """

    paid_text = f"""Найдено: {all_forks_count} вилок \n
    С прибылью более {FREE_PER_LIMIT}: {paid_forks_count} вилок
    С прибылью до {FREE_PER_LIMIT}: {free_forks_count} вилок
    """

    if not is_subscribed:
        RAW_FORKS_LIST = FREE_RAW_FORKS_LIST
        text_1 = f"Чтобы получать вилки с прибылью более {FREE_PER_LIMIT}% необходима премиум подписка. Оформить подписку можно через Telegram"
    else:
        text_1 = f""

    for fork in RAW_FORKS_LIST:
        event_name = (fork['team_1'], fork['team_2'], fork['event_date'])
        fork['event_id'] = hash(event_name)
        sport_info = SPORTS_MAPPER.get(fork['sport_name'])
        fork['sport_name'] = sport_info['name']
        fork['sport_icon'] = sport_info['icon']
        fork['sport_color'] = sport_info['color']
        
    events_map = {}
    for fork in RAW_FORKS_LIST:
        event_id = fork['event_id']
        if event_id not in events_map:
            events_map[event_id] = []
        events_map[event_id].append(fork)
    
    # Удаляем внешнюю таблицу, теперь каждый блок — это своя таблица
    main_page_content_html = '' 
    for event_id, forks_list in events_map.items():
        if forks_list:
            # Каждый вызов generate_fork_block_html возвращает готовую <table>...</table>
            main_page_content_html += generate_fork_block_html(forks_list[0], include_event_link=True) 
    
    event_pages_html = ""
    for event_id, forks_list in events_map.items():
        if forks_list:
            # Также удаляем внешнюю таблицу здесь
            event_page_table_html = ''
            for fork in forks_list:
                event_page_table_html += generate_fork_block_html(fork, include_event_link=False)
            
            # Используем первый элемент списка для получения названия команд
            event_pages_html += textwrap.dedent(f"""
            <div id="{event_id}" class="page">
                <p><a href="#" onclick="showPage('main-page')">← Вернуться к списку лучших вилок</a></p>
                <h2>Все вилки матча: {forks_list[0]['team_1']} vs {forks_list[0]['team_2']}</h2>
                {event_page_table_html}
            </div>
            """)


    html_content = textwrap.dedent(f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LiteForks</title>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background-color: #f0f0f0; color: #333; }}
            .header {{ 
                background-color: #000; 
                color: #fff; 
                padding: 10px 20px; 
                display: flex; 
                align-items: center;
                justify-content: space-between; /* ДОБАВЛЕНО: Распределяет элементы по ширине */
                width: 100%; /* ДОБАВЛЕНО: Гарантирует полную ширину */
                box-sizing: border-box; /* Учитывает padding в ширине */
            }}
            .header a {{ color: inherit; text-decoration: none; display: flex; align-items: center; }}
            .logo-placeholder {{ width: 40px; height: 40px; background-color: #007bff; margin-right: 15px; border-radius: 50%; }}
            .service-title {{ font-size: 1.5em; font-weight: bold; }}
            .main-container {{ display: flex; }}
            .sidebar {{ width: 200px; background-color: #fff; padding: 15px; height: 100vh; box-shadow: 2px 0 5px rgba(0,0,0,0.1); }}
            .sidebar .clock {{ font-size: 1.2em; font-weight: bold; margin-bottom: 20px; text-align: center; color: #333; }}
            .sidebar ul {{ list-style-type: none; padding: 0; }}
            .sidebar li a {{ display: block; padding: 10px 0; text-decoration: none; color: #333; border-bottom: 1px solid #ddd; }}
            
            .content-area {{ flex-grow: 1; padding: 20px; }}
            .page {{ display: none; }}
            .page.active {{ display: block; }}
            
            /* Стили Калькулятора */
            .calculator-option {{ margin-bottom: 20px; border: 1px solid #ccc; padding: 15px; background-color: #fff; }}
            .calculator-option h4 {{ margin-top: 0; }}
            .calculator-input-group {{ margin-bottom: 10px; }}
            .calculator-input-group input {{ padding: 8px; margin-right: 10px; width: 100px; }}
            .calculator-option button {{ padding: 10px 15px; background-color: #007bff; color: white; border: none; cursor: pointer; }}
            .calculator-result {{ margin-top: 15px; padding: 10px; background-color: #e9e9e9; white-space: pre-wrap; }}
            
            /* Стили Таблицы Вилок (изменены) */
            .forks-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: #fff; }}
            .fork-block {{ display: table-row-group; }}
            .fork-block td, .fork-block th {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
            .fork-header-row {{  font-weight: bold; }}
            .sport-icon {{ margin-right: 10px; font-size: 1.2em; }}
            .event-info-row {{ background-color: #fff; }}
            .event-info-row a {{ color: #007bff; cursor: pointer; text-decoration: underline; }}
            .profit-value {{ color: green; font-size: 1.1em; }}
            .bets-header-row {{ background-color: #eee; font-size: 0.9em; }}
            .service-logo {{
                width: 45px;
                height: 50px;
                margin-right: 10px;
                object-fit: cover;
            }}
            .service-title {{ 
                font-size: 1.5em; 
                font-weight: bold;
                font-style: italic;
            }}
            .user-profile-area {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            .user-info {{
                display: flex;
                align-items: center;
                color: #fff;
            }}
            .user-icon {{
                font-size: 1.5em;
                margin-right: 8px;
            }}
            .logout-btn {{
                padding: 8px 12px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
            }}
            .logout-btn:hover {{
                background-color: #c82333;
            }}
            .telegram-promo-block {{
                margin-top: 40px; /* <-- ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ: Отступ сверху */
                text-align: center; /* Центрирует кнопку */
                padding: 10px 0;
                text-decoration: none !important;
            }}

            .telegram-btn {{
                display: inline-block;
                padding: 10px 15px;
                background-color: #0088cc;
                color: white;
                text-decoration: none !important;
                border-radius: 5px;
                font-weight: bold;
                font-size: 0.9em;
                transition: background-color 0.3s;
            }}
            .telegram-btn:hover {{
                background-color: #007bb5;
                text-decoration: none !important; /* <-- УБИРАЕТ ПОДЧЕРКИВАНИЕ ПРИ НАВЕДЕНИИ КУРСОРА */
            }}
            .telegram-icon {{
                width: 20px;   /* Регулируйте размер иконки */
                height: auto;  /* Сохраняет пропорции */
                margin-right: 4px; /* Отступ между иконкой и текстом */
                vertical-align: middle; /* Выравнивает иконку по центру текста */
            }}
                                
                            
        </style>
    </head>
    <body>
        <div class="header">
            <a href="#" onclick="showPage('main-page'); return false;">
                <img src="{LOGO_SRC}" alt="Логотип Сервиса" class="service-logo">
                <div class="service-title">LiteForks</div>
            </a>
            <div class="user-profile-area">
                <div class="user-info">
                    <span class="user-icon">👤</span> <!-- Иконка пользователя -->
                    <span>ID: <strong id="user-id">{user_id}</strong></span> <!-- ID пользователя -->
                </div>
                <a href="/logout" class="logout-btn">Выйти</a>
            </div>
        </div>

        <div class="main-container">
            <div class="sidebar">
                <div class="clock" id="digital-clock"></div>
                <ul>
                    <li><a href="#" onclick="showPage('main-page')">🏠 Лучшие вилки</a></li>
                    <li><a href="#" onclick="showPage('fork-calculator-page')">🧮 Калькулятор вилок</a></li>
                    <li><a href="#" onclick="showPage('info-page')">ℹ️ Информация о вилках</a></li>
                </ul>
               <div class="telegram-promo-block"> 
               <a href="https://t.me/LiteForksBot" target="_blank" class="telegram-btn"> 
               <img src="static/telegram_2.svg" alt="Telegram Icon" class="telegram-icon">
                    Перейти в Telegram
               </a>
               </div>
            </div>

            <div class="content-area">
                
                <!-- ГЛАВНАЯ СТРАНИЦА -->
                <div id="main-page" class="page active">
                    <h2>Лучшие вилки (по событиям)</h2>
                    <p>Количество вилок всего:&nbsp; <strong>{all_forks_count}</strong></p>
                    <p>Количество вилок с прибылью более {FREE_PER_LIMIT}%:&nbsp; <strong>{paid_forks_count}</strong></p>
                    <p>Количество вилок с прибылью до {FREE_PER_LIMIT}%:&nbsp; <strong>{free_forks_count}</strong></p>
                    <strong>{text_1}</strong>
                    {main_page_content_html}
                </div>

                <!-- СТРАНИЦЫ СОБЫТИЙ -->
                {event_pages_html}

                <!-- СТРАНИЦА КАЛЬКУЛЯТОРА ВИЛОК (Обновленная разметка для 4х типов) -->
                <div id="fork-calculator-page" class="page">
                    <h2>Калькулятор Вилок (4 типа)</h2>
                    <p>Выберите вариант вилки и введите коэффициенты. <a href="#" onclick="showPage('info-page')">Подробнее о типах вилок →</a></p>

                    <!-- Вариант 1: 2 исхода (П1/П2 или Ф1/Ф2) -->
                    <div class="calculator-option">
                        <h4>Тип 1: 2 исхода (ТБ/ТМ или Ф1/Ф2) - Стандартная формула </h4>
                        <div class="calculator-input-group">
                            Кэф 1: <input type="number" id="c_odd1_1" step="0.01" value="2.1"> 
                            Кэф 2: <input type="number" id="c_odd2_1" step="0.01" value="1.9">
                        </div>
                        Общая сумма ставки: <input type="number" id="c_total_stake_1" step="any" value="1000">
                        <button onclick="calculateForkType(1)">Рассчитать</button>
                        <pre class="calculator-result" id="c_result_1"></pre>
                    </div>

                    <!-- Вариант 2: 3 исхода (1X2 - Стандартный) -->
                    <div class="calculator-option">
                        <h4>Тип 2: 3 исхода (П1-Х-П2) - Стандартная формула</h4>
                        <div class="calculator-input-group">
                            Кэф 1: <input type="number" id="c_odd1_2" step="0.01" value="4.3">
                            Кэф 2 (Ничья): <input type="number" id="c_odd2_2" step="0.01" value="9.2">
                            Кэф 3: <input type="number" id="c_odd3_2" step="0.01" value="1.49">
                        </div>
                        Общая сумма ставки: <input type="number" id="c_total_stake_2" step="any" value="1000">
                        <button onclick="calculateForkType(2)">Рассчитать</button>
                        <pre class="calculator-result" id="c_result_2"></pre>
                    </div>

                    <!-- Вариант 3: 3 исхода (Сложная формула 3) -->
                    <div class="calculator-option">
                        <h4>Тип 3: 3 исхода (Ф1(0)-Х-П2) - Сложная формула</h4>
                        <div class="calculator-input-group">
                            Кэф 1: <input type="number" id="c_odd1_3" step="0.01" value="2.0">
                            Кэф 2: <input type="number" id="c_odd2_3" step="0.01" value="3.5">
                            Кэф 3: <input type="number" id="c_odd3_3" step="0.01" value="4.0">
                        </div>
                        Общая сумма ставки: <input type="number" id="c_total_stake_3" step="any" value="1000">
                        <button onclick="calculateForkType(3)">Рассчитать</button>
                        <pre class="calculator-result" id="c_result_3"></pre>
                    </div>

                    <!-- Вариант 4: 3 исхода (Сложная формула 4) -->
                    <div class="calculator-option">
                        <h4>Тип 4: 3 исхода (Ф1(0)-Ф2(+0.5)-Ф21(-0.5)) - Сложная формула </h4>
                        <div class="calculator-input-group">
                            Кэф 1: <input type="number" id="c_odd1_4" step="0.01" value="1.8">
                            Кэф 2: <input type="number" id="c_odd2_4" step="0.01" value="2.5">
                            Кэф 3: <input type="number" id="c_odd3_4" step="0.01" value="3.0">
                        </div>
                        Общая сумма ставки: <input type="number" id="c_total_stake_4" step="any" value="1000">
                        <button onclick="calculateForkType(4)">Рассчитать</button>
                        <pre class="calculator-result" id="c_result_4"></pre>
                    </div>

                </div>

                <!-- НОВАЯ СТРАНИЦА ИНФОРМАЦИИ -->
                <div id="info-page" class="page">
                    <h2>Информация о типах вилок</h2>
                    <p>Здесь представлена информация о четырех типах расчета вилок, доступных в калькуляторе. Приведены несколько примеров вилок каждого типа. На данный момент используются только наиболее популярные варианты вилок. В дальнейшем планируется расширить диапозон различных вариантов вилок</p>
                    
                    <h3>Тип 1: 2 исхода (ТБ/ТМ или Ф1/Ф2) - Стандартная формула</h3>
                    <p>Самый простой и распространенный тип вилки, например, П1/П2, ТБ/ТМ. Расчет основан на стандартной формуле суммы обратных коэффициентов.</p>
                    <p> Варианты вилок: </p>
                    <ul class="fork-options-list">
                        <li><strong> "Тотал_Меньше0.5", "Тотал_Больше0.5" </strong> </li>
                        <li><strong> "ИндТотал_Ком1_Меньше0.5", "ИндТотал_Ком1_Больше0.5" </strong> </li>
                        <li><strong> "Фора_Ком1+0.5", "Фора_Ком2-0.5" </strong> </li>
                        <li><strong> "Забьют_Ком1Да", "Забьют_Ком1Нет" </strong> </li>
                    </ul>
                    <h3>Тип 2: 3 исхода (П1-Х-П2) - Стандартная формула</h3>
                    <p>Стандартный расчет для ставок на исход матча (П1, Ничья, П2). Также использует сумму обратных коэффициентов.</p>
                    <p> Варианты вилок: </p>
                    <ul class="fork-options-list">
                        <li><strong> "Исход_Победа1", "Исход_Ничья", "Исход_Победа2" </strong> </li>
                    </ul>
                    <h3>Тип 3: 3 исхода (Ф1(0)-Х-П2) - Сложная формула</h3>
                    <p> Используется специальная формула где возврат части ставки влияет на расчет общей прибыли и распределение сумм.</p>
                    <p> Варианты вилок: </p>
                    <ul class="fork-options-list">
                        <li><strong> "Фора_Ком10", "Исход_Ничья", "Исход_Победа2" </strong> </li>
                    </ul>
                    <h3>Тип 4: 3 исхода (Ф1(0)-Ф2(+0.5)-Ф21(-0.5)) - Сложная формула</h3>
                    <p> Используется специальная формула где возврат части ставки влияет на расчет общей прибыли и распределение сумм.</p>
                    <p> Варианты вилок: </p>
                    <ul class="fork-options-list">
                        <li><strong> "Тотал_Больше1", "Тотал_Меньше1.5", "Тотал_Меньше0.5" </strong> </li>
                        <li><strong> "Фора_Ком10", "Исход_Победа2Ничья", "Исход_Победа2" </strong> </li>
                        <li><strong> "Фора_Ком10", "Фора_Ком2+0.5", "Фора_Ком2-0.5" </strong> </li>
                    </ul>
                </div>

            </div>
        </div>

        <!-- JAVASCRIPT ДЛЯ ВСЕЙ ЛОГИКИ -->
        <script>
            // --- ОСНОВНЫЕ ФУНКЦИИ (showPage, updateClock) ---
            function showPage(pageId) {{
                const pages = document.querySelectorAll('.page');
                pages.forEach(page => {{
                    page.classList.remove('active');
                }});
                const activePage = document.getElementById(pageId);
                if (activePage) {{
                    activePage.classList.add('active');
                    window.scrollTo(0, 0); 
                }}
            }}
            function updateClock() {{
                const options = {{ hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }};
                document.getElementById('digital-clock').textContent = new Date().toLocaleTimeString('ru-RU', options);
            }}
            setInterval(updateClock, 1000);
            updateClock();
            
            function finalSafeJump(targetUrl, baseUrl, bkDomain) {{
                const newWindow = window.open('about:blank', '_blank');
                if (!newWindow) return;

                const jumperCode = `
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="referrer" content="no-referrer">
                        <style>
                            body {{ 
                                background: #e7ebf0; /* Цвет фона Telegram */
                                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                                display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; 
                            }}
                            .messenger-card {{ 
                                background: white; border-radius: 10px; padding: 25px; 
                                box-shadow: 0 1px 3px rgba(0,0,0,0.15); max-width: 380px; width: 90%; text-align: center; 
                            }}
                            .icon-box {{ 
                                width: 54px; height: 54px; background: #24A1DE; border-radius: 50%; 
                                margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;
                            }}
                            .icon-svg {{ fill: white; width: 28px; height: 28px; }}
                            .title {{ font-weight: 600; font-size: 17px; margin-bottom: 10px; color: #222; }}
                            .info {{ font-size: 14px; color: #707579; margin-bottom: 25px; line-height: 1.5; }}
                            .bk-name {{ color: #24A1DE; font-weight: 600; }}
                            .btn {{ 
                                display: block; padding: 12px; background: #24A1DE; color: white; 
                                text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 14px; 
                                transition: background 0.2s; cursor: pointer; border: none;
                            }}
                            .btn:hover {{ background: #2087ba; }}
                        </style>
                    </head>
                    <body>
                        <div class="messenger-card">
                            <div class="icon-box">
                                <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
                            </div>
                            <div class="title">Переход по ссылке</div>
                            <p class="info">Вы открываете внешнюю ссылку на событие в <span class="bk-name">${{bkDomain}}</span> через мессенджер Telegram.</p>
                            
                            <a href="${{targetUrl}}" rel="noreferrer" class="btn" onclick="window.opener=null;">ОТКРЫТЬ В БРАУЗЕРЕ</a>
                        </div>
                    </body>
                    </html>
                `;

                newWindow.document.write(jumperCode);
                newWindow.document.close();
            }}





            // --- ЛОГИКА КАЛЬКУЛЯТОРА ВИЛОК (JavaScript) ---

            /**
             * Вспомогательная функция для отображения результатов.
             * @param {{number}} type - Тип калькулятора (1, 2, 3, 4)
             * @param {{boolean}} isFork - Является ли вилкой
             * @param {{number}} profit - Процент прибыли
             * @param {{Array<number>}} stakes - Рассчитанные суммы ставок
             * @param {{Array<number>}} odds - Использованные коэффициенты
             */
            function setCalcResult(type, isFork, profit, stakes, odds) {{
                const resultEl = document.getElementById(`c_result_${{type}}`); 
                const totalStake = parseFloat(document.getElementById(`c_total_stake_${{type}}`).value);
                let resultText = "";

                if (isFork) {{
                    resultEl.style.backgroundColor = '#d4edda'; // Green
                    resultEl.style.color = '#155724';
                    resultText = `✅ Найдена вилка! Прибыль: ${{profit.toFixed(2)}}%\\n\\nРаспределение ставок при общей сумме ${{totalStake.toFixed(2)}} RUB:\\n`;
                    
                    stakes.forEach((stake, i) => {{
                        const percent = (stake * 100 / totalStake).toFixed(2);
                        resultText += `  Ставка ${{i + 1}}: ${{percent}}% ${{stake.toFixed(2)}} RUB (Коэф: ${{odds[i]}})\\n`;
                    }});
                }} else {{
                    resultEl.style.backgroundColor = '#f8d7da'; // Red
                    resultEl.style.color = '#721c24';
                    resultText = `❌ Это не вилка. Прибыль/убыток: ${{profit.toFixed(2)}}%`;
                }}
                resultEl.innerText = resultText;
            }}

            /**
             * Основная функция-диспетчер для всех типов калькулятора.
             * @param {{number}} type - Тип калькулятора (1, 2, 3, 4)
             */
            function calculateForkType(type) {{
                const nominal_value = parseFloat(document.getElementById(`c_total_stake_${{type}}`).value);
                const resultDiv = document.getElementById(`c_result_${{type}}`);
                resultDiv.innerText = '';
                resultDiv.style.backgroundColor = '#e9e9e9';

                let k1, k2, k3, s, v1, v2, v3, values, profit, maxReturn;
                
                if (isNaN(nominal_value) || nominal_value <= 0) {{
                    resultDiv.textContent = "Введите корректную сумму.";
                    resultDiv.style.color = "red";
                    return;
                }}

                switch (type) {{
                    case 1:
                        k1 = parseFloat(document.getElementById(`c_odd1_${{type}}`).value);
                        k2 = parseFloat(document.getElementById(`c_odd2_${{type}}`).value);
                        if (isNaN(k1) || isNaN(k2) || k1 <= 1 || k2 <= 1) {{
                             resultDiv.textContent = "Введите корректные коэффициенты (> 1).";
                             resultDiv.style.color = "red"; return;
                        }}
                        s = 1/k1 + 1/k2;
                        if (s >= 1) {{ setCalcResult(type, false, (1/s - 1) * 100, [], []); return; }}
                        v1 = (nominal_value * (1/k1)) / s;
                        v2 = (nominal_value * (1/k2)) / s;
                        values = [v1, v2];
                        maxReturn = Math.max(v1*k1, v2*k2);
                        profit = (maxReturn / nominal_value - 1) * 100;
                        setCalcResult(type, true, profit, values, [k1, k2]);
                        break;

                    case 2:
                        k1 = parseFloat(document.getElementById(`c_odd1_${{type}}`).value);
                        k2 = parseFloat(document.getElementById(`c_odd2_${{type}}`).value);
                        k3 = parseFloat(document.getElementById(`c_odd3_${{type}}`).value);
                        if (isNaN(k1) || isNaN(k2) || isNaN(k3) || k1 <= 1 || k2 <= 1 || k3 <= 1) {{
                             resultDiv.textContent = "Введите корректные коэффициенты (> 1).";
                             resultDiv.style.color = "red"; return;
                        }}
                        s = 1/k1 + 1/k2 + 1/k3;
                        if (s >= 1) {{ setCalcResult(type, false, (1/s - 1) * 100, [], []); return; }}
                        v1 = (nominal_value * (1/k1)) / s;
                        v2 = (nominal_value * (1/k2)) / s;
                        v3 = (nominal_value * (1/k3)) / s;
                        values = [v1, v2, v3];
                        maxReturn = Math.max(v1*k1, v2*k2, v3*k3);
                        profit = (maxReturn / nominal_value - 1) * 100;
                        setCalcResult(type, true, profit, values, [k1, k2, k3]);
                        break;

                    case 3:
                        k1 = parseFloat(document.getElementById(`c_odd1_${{type}}`).value);
                        k2 = parseFloat(document.getElementById(`c_odd2_${{type}}`).value);
                        k3 = parseFloat(document.getElementById(`c_odd3_${{type}}`).value);
                         if (isNaN(k1) || isNaN(k2) || isNaN(k3) || k1 <= 1 || k2 <= 1 || k3 <= 1) {{
                             resultDiv.textContent = "Введите корректные коэффициенты (> 1).";
                             resultDiv.style.color = "red"; return;
                        }}
                        s = 1/k1 + 1/k3 + (k1-1)/(k2*k1);
                        if (s >= 1) {{ setCalcResult(type, false, (1/s - 1) * 100, [], []); return; }}
                        v1 = nominal_value/(1 + (k1-1)/k2 + k1/k3);
                        v2 = (k1-1)*v1/k2;
                        v3 = k1*v1/k3;
                        values = [v1, v2, v3];
                        maxReturn = Math.max(v1*k1, v2*k2 + v1, v3*k3);
                        profit = (maxReturn / nominal_value - 1) * 100;
                        setCalcResult(type, true, profit, values, [k1, k2, k3]);
                        break;

                    case 4:
                        k1 = parseFloat(document.getElementById(`c_odd1_${{type}}`).value);
                        k2 = parseFloat(document.getElementById(`c_odd2_${{type}}`).value);
                        k3 = parseFloat(document.getElementById(`c_odd3_${{type}}`).value);
                         if (isNaN(k1) || isNaN(k2) || isNaN(k3) || k1 <= 1 || k2 <= 1 || k3 <= 1) {{
                             resultDiv.textContent = "Введите корректные коэффициенты (> 1).";
                             resultDiv.style.color = "red"; return;
                        }}
                        s = 1/k1 + 1/(k1*k3) + (k1-1)/(k2*k1);
                        if (s >= 1) {{ setCalcResult(type, false, (1/s - 1) * 100, [], []); return; }}
                        v1 = nominal_value/(1+1/k3+(k1-1)/k2);
                        v2 = (k1-1)*v1/k2;
                        v3 = v1/k3;
                        values = [v1, v2, v3];
                        maxReturn = Math.max(v1*k1, v2*k2 + v1, v3*k3 + v2*k2);
                        profit = (maxReturn / nominal_value - 1) * 100;
                        setCalcResult(type, true, profit, values, [k1, k2, k3]);
                        break;
                }}
            }}
        </script>
    </body>
    </html>
    """)

    return html_content


class TokenForm(FlaskForm):
    # Поле Token: Обязательно для заполнения, длина от 5 до 50 символов
    token = StringField('Введите Токен', validators=[DataRequired(), Length(min=5, max=50)])
    submit = SubmitField('Подтвердить')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Пожалуйста, введите токен для доступа к основному функционалу.", "warning")
            return redirect(url_for('validate_token'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    # Проверяем, авторизован ли пользователь и активна ли его подписка
    if session.get('logged_in') and session.get('is_subscribed'):
        return redirect(url_for('main'))
    return redirect(url_for('validate_token'))


@app.route('/validate_token', methods=['GET', 'POST'])
def validate_token():
    form = TokenForm()

    if form.validate_on_submit():
        
        user_token = form.token.data
        USERS_DATA = get_json_data_from_git(path=USERS_FILE_PATH)

        if user_token in USERS_DATA: 
            user_data = USERS_DATA[user_token]
            
            is_subscribed = user_data.get('is_subscribed', False)        

            # Если все ОК, сохраняем данные в сессию
            session['logged_in'] = True
            session['user_id'] = user_data['user_id']
            session['is_subscribed'] = is_subscribed

            return redirect(url_for('main'))
        else:
            flash('Неверный токен. Попробуйте еще раз.', 'error')
            return render_template('token_form.html', form=form)

    return render_template('token_form.html', form=form)


@app.route('/main')
@login_required 
def main():
    forks_data = get_json_data_from_git(path=DATA_FILE_PATH)
    html_content = create_service_html(
        forks_data=forks_data, 
        is_subscribed=session['is_subscribed'],
        user_id=session['user_id']
    )
    return render_template_string(html_content)


@app.route('/logout')
def logout():
    session.pop('logged_in', None) 
    session.pop('user_id', None)
    session.pop('is_subscribed', None)
    flash("Вы вышли из системы.", "info")
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
