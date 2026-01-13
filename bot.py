import telebot
import sqlite3
import uuid
import json
import requests
from datetime import datetime, timedelta

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = '8570392401:AAFfowtqYzjxz-PCC-0IVJPx1xl5V03LCXk'
XUI_PANEL_URL = 'http://31.130.131.214:43449'  # БЕЗ слеша в конце!
XUI_BASE_PATH = '/5LwcfqTGQp8svE2Dmx'          # Твой кастомный путь
XUI_USERNAME = 'ixCKyeJTUl'                    # Логин от панели
XUI_PASSWORD = '3tEgwrJFCG'                    # Пароль от панели
INBOUND_ID = 1                                  # ID твоего Inbound в X-UI
VPN_SERVER = '31.130.131.214'                  # Твой IP сервера
VPN_PORT = 443                                  # Порт твоего сервера (Reality)
REALITY_PUBLIC_KEY = 'Z6HRfh6kFc5iYeGDYN3CI6oh8HvYbbxgGJkRedVAAis'                         # Свой публичный ключ Reality
SHORT_ID = 'f717c70e'                                   # Свой Short ID
SERVER_NAME = 'www.microsoft.com'              # SNI (любой крупный сайт)
# ===============================

bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к базе данных
def get_db():
    conn = sqlite3.connect('vpn_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

# Инициализация базы данных
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            uuid TEXT UNIQUE,
            created_at TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Авторизация в X-UI и получение токена
def get_xui_token():
    auth_url = f"{XUI_PANEL_URL}{XUI_BASE_PATH}/login"  # Учитываем BASE_PATH
    data = {"username": XUI_USERNAME, "password": XUI_PASSWORD}
    try:
        response = requests.post(auth_url, json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            print(f"Ошибка авторизации: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка подключения к X-UI: {e}")
        return None

# Создание пользователя в X-UI
def create_xui_user():
    token = get_xui_token()
    if not token:
        return None
    
    headers = {'Authorization': f'Bearer {token}'}
    user_uuid = str(uuid.uuid4())
    
    # Данные для создания пользователя
    user_data = {
        "up": 0,
        "down": 0,
        "total": 0,  # 0 = безлимит
        "remark": f"user_{user_uuid[:8]}",
        "enable": True,
        "expiryTime": 0,  # 0 = бессрочно
        "clientStats": [{
            "id": user_uuid,
            "email": f"{user_uuid}@vpn.com",
            "enable": True,
            "totalGB": 0,  # Безлимит
            "expiryTime": 0
        }]
    }
    
    # URL с учетом BASE_PATH
    url = f"{XUI_PANEL_URL}{XUI_BASE_PATH}/api/inbounds/{INBOUND_ID}/clients"
    response = requests.post(url, json=user_data, headers=headers, timeout=10)
    
    if response.status_code == 200:
        return user_uuid
    else:
        print(f"Ошибка создания пользователя: {response.status_code}")
        print(f"Ответ сервера: {response.text}")
        return None

# Генерация полного конфига в формате JSON
def generate_full_config(user_uuid):
    config_template = {
        "dns": {
            "hosts": {"domain:googleapis.cn": "googleapis.com"},
            "queryStrategy": "UseIPv4",
            "servers": [
                "1.1.1.1",
                {"address": "1.1.1.1", "domains": [], "port": 53},
                {"address": "8.8.8.8", "domains": [], "port": 53}
            ]
        },
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": 10808,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True, "userLevel": 8},
                "sniffing": {"destOverride": ["http", "tls", "quic"], "enabled": True},
                "tag": "socks"
            },
            {
                "listen": "127.0.0.1",
                "port": 10809,
                "protocol": "http",
                "settings": {"userLevel": 8},
                "sniffing": {"destOverride": ["http", "tls", "quic"], "enabled": True},
                "tag": "http"
            }
        ],
        "log": {"loglevel": "error"},
        "outbounds": [
            {
                "mux": {"concurrency": -1, "enabled": False, "xudpConcurrency": 8, "xudpProxyUDP443": ""},
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": VPN_SERVER,
                        "port": VPN_PORT,
                        "users": [{
                            "encryption": "none",
                            "flow": "xtls-rprx-vision",
                            "id": user_uuid,  # ВСТАВЛЯЕМ реальный UUID
                            "level": 8,
                            "security": "auto"
                        }]
                    }]
                },
                "streamSettings": {
                    "network": "tcp",
                    "realitySettings": {
                        "allowInsecure": False,
                        "fingerprint": "chrome",
                        "publicKey": REALITY_PUBLIC_KEY,  # ТВОЙ ключ
                        "serverName": SERVER_NAME,
                        "shortId": SHORT_ID,  # ТВОЙ Short ID
                        "show": False,
                        "spiderX": "/"
                    },
                    "security": "reality",
                    "tcpSettings": {"header": {"type": "none"}}
                },
                "tag": "proxy"
            },
            {
                "protocol": "freedom",
                "settings": {"domainStrategy": "UseIP"},
                "tag": "direct"
            }
        ],
        "policy": {
            "levels": {
                "0": {"statsUserDownlink": True, "statsUserUplink": True},
                "8": {"connIdle": 300, "downlinkOnly": 1, "handshake": 4, "uplinkOnly": 1}
            },
            "system": {
                "statsInboundDownlink": True,
                "statsInboundUplink": True,
                "statsOutboundDownlink": True,
                "statsOutboundUplink": True
            }
        },
        "remarks": f"⚡ Создано ботом | {datetime.now().strftime('%d.%m.%Y')}",
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": []
        },
        "stats": {}
    }
    return config_template

# Сохранение пользователя в базу данных
def save_user_to_db(user_id, user_uuid):
    conn = get_db()
    cursor = conn.cursor()
    expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO users (user_id, uuid, created_at, expires_at) VALUES (?, ?, ?, ?)',
                   (user_id, user_uuid, datetime.now(), expires_at))
    conn.commit()
    conn.close()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Привет! Я бот для создания VPN-подключений.\n\nИспользуй команду /getkey чтобы получить конфигурацию.")

# Обработчик команды /getkey
@bot.message_handler(commands=['getkey'])
def send_config(message):
    try:
        user_id = message.from_user.id
        bot.send_message(message.chat.id, "🔄 Создаю для тебя конфигурацию...")
        
        # 1. Создаем пользователя в X-UI
        user_uuid = create_xui_user()
        if not user_uuid:
            bot.send_message(message.chat.id, "❌ Ошибка создания ключа. Попробуй позже.")
            return
        
        # 2. Сохраняем в базу данных
        save_user_to_db(user_id, user_uuid)
        
        # 3. Генерируем полный конфиг
        config = generate_full_config(user_uuid)
        config_json = json.dumps(config, indent=2, ensure_ascii=False)
        
        # 4. Отправляем файлом
        bot.send_document(message.chat.id, ('config.json', config_json.encode('utf-8')), caption="✅ Твой конфиг готов! Импортируй его в HAPP или V2RayN.")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}")

# Запуск бота
if __name__ == '__main__':
    init_db()
    print("Бот запущен...")
    bot.infinity_polling()
