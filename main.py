import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://your-app.onrender.com/webhook

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a prompt, and I will generate an image for you using Pollinations AI."
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text(f"Generating image for: {prompt}")
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt}"
        response = requests.get(url)
        if response.status_code == 200:
            with open("temp.jpg", "wb") as f:
                f.write(response.content)
            await update.message.reply_photo(photo=open("temp.jpg", "rb"))
        else:
            await update.message.reply_text("Sorry, I couldn't generate the image.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# Set up Telegram application
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

# FastAPI webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}

# Set webhook on startup
@app.on_event("startup")
async def set_webhook():
    await bot.set_webhook(url=WEBHOOK_URL)

# Root endpoint
@app.get("/")
async def root():
    return {"status": "Bot is running"}
