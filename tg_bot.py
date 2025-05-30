from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from flask import Flask
import requests
import os
from dotenv import load_dotenv
from threading import Thread

# --- Загрузка переменных окружения ---
load_dotenv()

# --- Переменные окружения ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LAWYER_TG_ID = int(os.getenv("LAWYER_TG_ID", "5981472079"))
VK_WEBHOOK_URL = os.getenv("VK_WEBHOOK_URL", "https://vk-tg-bankruptcy-bot.onrender.com/webhook/telegram ")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не установлен TELEGRAM_BOT_TOKEN в .env или в переменных окружения")

# --- Состояния FSM ---
CREATE_POST, SEND_ALL, GENERATE_PDF = range(3)

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["Создать пост", "Рассылка всем"], ["Сформировать PDF"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    
    await update.message.reply_text(
        "Здравствуйте! Выберите действие:",
        reply_markup=markup
    )

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите текст поста:")
    return CREATE_POST

async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите текст для рассылки:")
    return SEND_ALL

async def generate_pdf_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите текст для PDF:")
    return GENERATE_PDF

# --- Обработка ввода ---
async def handle_create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_text = update.message.text
    try:
        response = requests.post(VK_WEBHOOK_URL, json={"text": post_text})
        if response.status_code == 200:
            await update.message.reply_text("Пост отправлен во ВК!")
        else:
            await update.message.reply_text(f"Ошибка: {response.status_code}")
    except Exception as e:
        print("Ошибка при отправке:", e)
        await update.message.reply_text("Не удалось отправить пост во ВК.")
    return ConversationHandler.END

async def handle_send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    from vk_bot import load_clients_db
    users = load_clients_db()  # предположим, что такая функция существует

    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text)
        except Exception as e:
            print(f"Не могу отправить {chat_id}: {e}")

    await update.message.reply_text("Рассылка завершена!")
    return ConversationHandler.END

async def handle_generate_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from fpdf import FPDF

    text = update.message.text
    pdf = FPDF()
    pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)

    for line in text.split('\n'):
        pdf.cell(0, 10, txt=line, ln=True)

    filename = "post.pdf"
    pdf.output(filename)
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(filename, "rb"))

    await update.message.reply_text("Ваш PDF создан!")
    return ConversationHandler.END

# --- Отмена диалога ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# === Flask сервер для Render.com ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram bot is running", 200

def run_server():
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

# --- Запуск бота ---
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("create_post", create_post),
            CommandHandler("send_all", send_all),
            CommandHandler("generate_pdf", generate_pdf_cmd)
        ],
        states={
            CREATE_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_create_post)],
            SEND_ALL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_send_all)],
            GENERATE_PDF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_generate_pdf)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    print("Telegram-бот запущен...")
    application.run_polling()

# --- Запуск Flask + Telegram бота ---
if __name__ == "__main__":
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()

    main()
