import os
import aiohttp
import random
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import urllib.parse

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = FastAPI()

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me a prompt and I will generate an image using Pollinations AI.\n"
        "Each time you send the same prompt, a new image will be generated!"
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text(f"🎨 Generating image for: {prompt}")
    try:
        encoded_prompt = urllib.parse.quote(prompt)

        seed = random.randint(1, 99999999)  # random seed every request
        url = f"https://pollinations.ai/p/{encoded_prompt}?seed={seed}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    await update.message.reply_photo(photo=image_bytes, caption=f"Seed: {seed}")
                else:
                    await update.message.reply_text("❌ Sorry, I couldn't generate the image.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

# Telegram app
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image))

# FastAPI startup/shutdown
@app.on_event("startup")
async def startup():
    await application.initialize()
    await application.start()
    await application.bot.delete_webhook()
    await application.bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def shutdown():
    await application.stop()
    await application.shutdown()

# Webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "Bot is running"}
