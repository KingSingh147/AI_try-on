from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8000))

app = FastAPI()
bot = Bot(token=BOT_TOKEN)

# Telegram Bot Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a prompt, and I will generate an image for you using Pollinations AI.")

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

# Telegram Bot Setup
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

# FastAPI routes
@app.on_event("startup")
async def on_startup():
    import asyncio
    asyncio.create_task(application.run_polling())

@app.get("/")
async def root():
    return {"status": "Bot is running"}
