from flask import Flask, request, jsonify
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import os
from dotenv import load_dotenv
import sqlite3
import json
import pandas as pd

load_dotenv()

app = Flask(__name__)

GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
GROUP_ID = os.getenv("VK_GROUP_ID")
CONFIRMATION_TOKEN = os.getenv("VK_CALLBACK_CONFIRMATION_TOKEN")

vk_session = vk_api.VkApi(token=GROUP_TOKEN)
vk = vk_session.get_api()

conn = sqlite3.connect('clients.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bankruptcy_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        city TEXT,
        debts TEXT,
        total_debt REAL,
        income REAL,
        property_info TEXT,
        court_cases TEXT,
        wants_bankruptcy TEXT
    )
''')
conn.commit()

@app.route('/callback', methods=['POST'])
def callback():
    data = request.json

    if data.get('type') == 'confirmation':
        return CONFIRMATION_TOKEN, 200

    elif data.get('type') == 'message_new':
        user_id = data['object']['message']['from_id']
        message_text = data['object']['message']['text'].strip().lower()

        if message_text in ['привет', 'start', 'старт']:
            buttons = ["Физическое лицо", "Юридическое лицо", "Взыскание долгов"]
            vk.messages.send(
                user_id=user_id,
                message="Выберите, кто вы:",
                keyboard=json.dumps({
                    "one_time": False,
                    "buttons": [[{"action": {"type": "text", "label": btn}} for btn in buttons]
                }, ensure_ascii=False),
                random_id=0
            )

    return 'ok', 200

@app.route('/webhook/telegram', methods=['POST'])
def receive_telegram_post():
    data = request.json
    post_text = data.get("text")
    if post_text:
        try:
            vk.wall.post(owner_id="-" + GROUP_ID, message=post_text, from_group=1)
            with open("posts_history.txt", "a") as f:
                f.write(f"{datetime.now()} - {post_text}\n")
            return jsonify({"status": "published"}), 200
        except Exception as e:
            print("Ошибка публикации:", e)
            return jsonify({"status": "failed", "error": str(e)}), 500
    return jsonify({"error": "no text"}), 400

@app.route('/admin')
def admin_panel():
    cursor.execute("SELECT * FROM bankruptcy_applications")
    applications = cursor.fetchall()
    return render_template('admin.html', clients=applications)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))