import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # Your Render service URL + /webhook

STAGE_PRODUCT, STAGE_MODEL = range(2)
user_state = {}

HF_API_URL = "https://api-inference.huggingface.co/models/IDM-VTON/IDM-VTON"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()
application = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update, context):
    user_state[update.message.chat_id] = {}
    await update.message.reply_text("Upload PRODUCT image 📸")
    return STAGE_PRODUCT

async def get_product(update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"product_{update.message.chat_id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["product"] = path
    await update.message.reply_text("Upload MODEL image 👤")
    return STAGE_MODEL

async def get_model(update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"model_{update.message.chat_id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["model"] = path
    await update.message.reply_text("⏳ Processing... 20–40 sec")

    files = {
        "garment_image": open(user_state[update.message.chat_id]["product"], "rb"),
        "person_image": open(user_state[update.message.chat_id]["model"], "rb"),
    }
    response = requests.post(HF_API_URL, headers=headers, files=files)
    output_url = response.json().get("output", None)

    if not output_url:
        await update.message.reply_text("⚠️ Error generating result.")
        return ConversationHandler.END

    await update.message.reply_photo(output_url)
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STAGE_PRODUCT: [MessageHandler(filters.PHOTO, get_product)],
        STAGE_MODEL: [MessageHandler(filters.PHOTO, get_model)],
    },
    fallbacks=[]
)

application.add_handler(conv)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.update_queue.put(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await bot.set_webhook(WEBHOOK_URL)
