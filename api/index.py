import textwrap
from datetime import datetime
import json
import base64
from datetime import datetime
from urllib.parse import parse_qs
import hashlib
import hmac
import os
import time

from flask import Flask, request, jsonify, render_template_string
app = Flask(__name__)


# TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "fallback_token")
TELEGRAM_BOT_TOKEN = "8385615154:AAEwVHr3LcUVkDAL5NiJSImOy2trol_YRp0"

PAID_FORKS_FILES = {
    'football': 'RESULTS/football/prod/paid.json'
}

FREE_FORKS_FILES = {
    'football': 'RESULTS/football/prod/free.json'
}
SPORTS_MAPPER = {
    'football': {
        'name': 'Футбол',
        'icon': "⚽",
        'color': "#f2e3bf"
    }
}
NOMINAL_VALUE = 1000
LOGO_PATH = 'static/logo.png'


USERS_DATA = {
    123456789: {'is_subscribed': True, 'username': 'testuser1'},
    987654321: {'is_subscribed': False, 'username': 'testuser2'},
}


def generate_fork_block_html(fork_data, include_event_link=False):
    event_time_fmt = datetime.strptime(fork_data['event_time'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
    created_time_fmt = datetime.fromisoformat(fork_data['created_time']).strftime('%d.%m.%Y %H:%M')
    bet_rows_html = ""
    for i in range(len(fork_data['bets_names'])):
        bet_rows_html += textwrap.dedent(f"""
        <tr class="bet-row">
            <td>{fork_data['bets_names'][i]}</td>
            <td>{fork_data['bets_values'][i]}</td>
            <td>{(fork_data['values'][i]/NOMINAL_VALUE * 100):.2f} %</td>
            <td>{fork_data['bookmakers'][i]}</td>
            <td><a href="{fork_data['events_urls'][i]}" target="_blank">🔗 Перейти</a></td>
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
                    <span class="sport-type">{fork_data['sport_name']}</span>
                </td>
            </tr>
            <tr class="event-info-row"><td colspan="2"><strong>Событие:</strong> {teams_display}</td><td><strong>Прибыль:</strong> <span class="profit-value">{(100*(fork_data['profit']-NOMINAL_VALUE)/NOMINAL_VALUE):.2f}%</span></td><td><strong>Начало:</strong> {event_time_fmt}</td><td><strong>Создано:</strong> {created_time_fmt}</td></tr>
            <tr class="bets-header-row"><th>Название ставки</th><th>Кэф.</th><th>Сумма ставки</th><th>Букмекер</th><th>Ссылка</th></tr>
            {bet_rows_html}
        </tbody>
    </table>
    """)


def create_service_html(is_subscribed):

    try:
        with open(LOGO_PATH, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode("utf-8")
            # Формируем data URL:
            logo_src = f"data:image/png;base64,{logo_data}"
    except FileNotFoundError:
        logo_src = ""
        print("Error: logo.png not found for Base64 encoding.")

    RAW_FORKS_LIST = []
    if is_subscribed:
        FORKS_FILES = PAID_FORKS_FILES.copy()
    else:
        FORKS_FILES = FREE_FORKS_FILES.copy()
    for sport_name, fork_file in FORKS_FILES.items():
        with open(fork_file, 'r') as f:
            json_data = json.load(f)
        for fork in json_data:
            fork['sport_name'] = sport_name
        RAW_FORKS_LIST.extend(json_data)

    RAW_FORKS_LIST = sorted(RAW_FORKS_LIST, key=lambda x: x['profit'], reverse=True)

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
            .header {{ background-color: #000; color: #fff; padding: 10px 20px; display: flex; align-items: center; }}
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
                width: 45px; /* Задайте нужный размер */
                height: 50px;
                margin-right: 10px; /* Отступ от названия сервиса */
                object-fit: cover; /* Чтобы изображение хорошо вписывалось в размеры */
            }}
            .service-title {{ 
                font-size: 1.5em; 
                font-weight: bold;
                font-style: italic; /* Делает текст курсивом */
                /* text-shadow: 1px 1px 2px #aaa; Можно добавить легкую тень для "красоты" */
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="#" onclick="showPage('main-page'); return false;">
                <img src="{logo_src}" alt="Логотип Сервиса" class="service-logo">
                <div class="service-title">LiteForks</div>
            </a>
        </div>

        <div class="main-container">
            <div class="sidebar">
                <div class="clock" id="digital-clock"></div>
                <ul>
                    <li><a href="#" onclick="showPage('main-page')">🏠 Лучшие вилки</a></li>
                    <li><a href="#" onclick="showPage('fork-calculator-page')">🧮 Калькулятор вилок</a></li>
                    <li><a href="#" onclick="showPage('info-page')">ℹ️ Информация о вилках</a></li>
                </ul>
            </div>

            <div class="content-area">
                
                <!-- ГЛАВНАЯ СТРАНИЦА -->
                <div id="main-page" class="page active">
                    <h2>Лучшие вилки (по событиям)</h2>
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


def verify_telegram_signature(data):
    # ... (Код функции verify_telegram_signature из предыдущих сообщений, без изменений) ...
    if 'hash' not in data: return False
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data.items()) if key != 'hash'
    )
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256)
    return hmac_hash.hexdigest() == data['hash']


@app.route('/')
def handle_all_requests():
    """
    Основная функция Vercel. 
    Получает запрос, проверяет параметры URL, генерирует и возвращает полный HTML.
    """
    is_subscribed = False

    # # 1. Извлекаем параметры из URL-строки запроса
    # query_string = request.query_string.decode('utf-8')
    # auth_data = parse_qs(query_string)
    # # parse_qs возвращает списки, нужно преобразовать в простые значения
    # auth_data = {k: v[0] for k, v in auth_data.items()}

    auth_data = request.args
    return jsonify(auth_data)

    # 2. Проверяем авторизацию Telegram
    if auth_data.get('id') and auth_data.get('hash'):
        if verify_telegram_signature(auth_data):
            # Проверяем срок годности данных

            user_id = int(auth_data.get('id'))
            user_info = USERS_DATA.get(user_id)
            if user_info and user_info['is_subscribed']:
                is_subscribed = True
                               
            result_html = create_service_html(is_subscribed=is_subscribed)

        else:
            result_html = "<p> Ошибка: Неверная подпись Telegram.</p>"
    else:
        result_html = "<p> Ошибка идентификации </p>"
    
    return render_template_string(result_html)
