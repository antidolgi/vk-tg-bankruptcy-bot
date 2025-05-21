from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import requests
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("LAWYER_TG_ID")
VK_WEBHOOK_URL = os.getenv("VK_WEBHOOK_URL")

def generate_pdf(text):
    pdf = FPDF()
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("DejaVu", size=12)

    for line in text.split('\n'):
        pdf.cell(0, 10, txt=line, ln=True)

    filename = "post.pdf"
    pdf.output(filename)
    return filename

async def start(update, context):
    await update.message.reply_text("Здравствуйте! Выберите действие:\n/create_post — создать пост\n/send_all — рассылка всем\n/generate_pdf — создать PDF из текста")

async def create_post(update, context):
    await update.message.reply_text("Введите текст поста:")
    context.user_data['mode'] = 'create_post'

async def send_all(update, context):
    await update.message.reply_text("Напишите текст для рассылки:")
    context.user_data['mode'] = 'send_all'

async def generate_pdf_cmd(update, context):
    await update.message.reply_text("Введите текст для PDF:")
    context.user_data['mode'] = 'generate_pdf'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if not mode:
        return

    text = update.message.text

    if mode == 'create_post':
        try:
            response = requests.post(VK_WEBHOOK_URL, json={"text": text})
            if response.status_code == 200:
                await update.message.reply_text("Пост отправлен во ВК!")
        except Exception as e:
            print("Ошибка отправки:", e)
            await update.message.reply_text("Не удалось отправить во ВК.")

    elif mode == 'send_all':
        from main import load_clients_db
        users = load_clients_db()
        for chat_id in users:
            try:
                await context.bot.send_message(chat_id=chat_id, text=text)
            except Exception as e:
                print(f"Не могу отправить {chat_id}: {e}")
        await update.message.reply_text("Рассылка завершена!")

    elif mode == 'generate_pdf':
        pdf_path = generate_pdf(text)
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(pdf_path, "rb"))
        await update.message.reply_text("Ваш PDF создан!")

    context.user_data['mode'] = None

app = Application().token(TELEGRAM_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("create_post", create_post))
app.add_handler(CommandHandler("send_all", send_all))
app.add_handler(CommandHandler("generate_pdf", generate_pdf_cmd))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Telegram-бот запущен...")
app.run_polling()
