import os
print("Token:", os.getenv("TELEGRAM_TOKEN"))

import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ---- Environment Variables ----
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # <-- MUST be full URL without /webhook/<token>

# ---- HuggingFace Model ----
HF_API_URL = "https://api-inference.huggingface.co/models/ovi054/virtual-tryon-kontext-lora"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# ---- Telegram Core ----
bot = Bot(TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# ---- FastAPI ----
app = FastAPI()

STAGE_PRODUCT, STAGE_MODEL = range(2)
user_state = {}


# ---------- BOT COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_chat.id] = {}
    await update.message.reply_text("📌 Step 1: Send CLOTH image first")
    return STAGE_PRODUCT


async def get_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    cloth = f"cloth_{update.effective_chat.id}.jpg"
    await photo.download_to_drive(cloth)
    user_state[update.effective_chat.id]["cloth"] = cloth
    await update.message.reply_text("📌 Step 2: Send MODEL image")
    return STAGE_MODEL


async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    model_img = f"model_{update.effective_chat.id}.jpg"
    await photo.download_to_drive(model_img)
    user_state[update.effective_chat.id]["model"] = model_img

    await update.message.reply_text("⏳ Please wait 30–60 sec while generating output...")

    files = {
        "garment_image": open(user_state[update.effective_chat.id]["cloth"], "rb"),
        "person_image": open(user_state[update.effective_chat.id]["model"], "rb"),
    }

    response = requests.post(HF_API_URL, headers=headers, files=files)
    result = response.content

    await update.message.reply_photo(result)
    return ConversationHandler.END


conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STAGE_PRODUCT: [MessageHandler(filters.PHOTO, get_product)],
        STAGE_MODEL: [MessageHandler(filters.PHOTO, get_model)],
    },
    fallbacks=[],
)
application.add_handler(conv)


# ---------- FASTAPI WEBHOOK ----------
@app.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != TELEGRAM_TOKEN:
        return {"status": "forbidden"}

    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}


@app.get("/")
def home():
    return {"status": "BOT IS RUNNING 🚀"}


# ---------- STARTUP ----------
@app.on_event("startup")
async def startup():
    await application.initialize()
    webhook_full = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    await application.bot.set_webhook(webhook_full)
    await application.start()
    print("Webhook set to:", webhook_full)
