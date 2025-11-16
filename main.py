import os
import aiohttp
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import urllib.parse

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = FastAPI()

# Shared aiohttp session for all requests
session: aiohttp.ClientSession | None = None

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a prompt, and I will generate an image for you using Pollinations AI."
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global session
    prompt = update.message.text
    await update.message.reply_text(f"Generating image for: {prompt}")
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        async with session.get(url) as response:
            if response.status == 200:
                image_bytes = await response.read()
                await update.message.reply_photo(photo=image_bytes)
            else:
                await update.message.reply_text("Sorry, I couldn't generate the image.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# Create Telegram Application
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

# FastAPI startup
@app.on_event("startup")
async def startup():
    global session
    session = aiohttp.ClientSession()  # shared session

    # Initialize bot properly
    await application.bot.initialize()

    # Initialize and start application
    await application.initialize()
    await application.start()

    # Set webhook
    await application.bot.delete_webhook()
    await application.bot.set_webhook(WEBHOOK_URL)
    print("Bot initialized and webhook set.")

# FastAPI shutdown
@app.on_event("shutdown")
async def shutdown():
    global session
    await application.stop()
    await application.shutdown()
    if session:
        await session.close()
    print("Bot shutdown complete.")

# Webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# Root endpoint
@app.get("/")
async def root():
    return {"status": "Bot is running"}
