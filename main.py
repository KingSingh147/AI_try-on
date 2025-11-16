import os
import io
import logging
import requests
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters
from huggingface_hub import InferenceClient
from PIL import Image

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Render URL + /webhook

STAGE_CLOTH, STAGE_MODEL = range(2)
user_state = {}

bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()
application = Application.builder().token(TELEGRAM_TOKEN).build()

# HuggingFace client (fal-ai provider)
client = InferenceClient(
    provider="fal-ai",
    api_key=HF_TOKEN
)


async def start(update, context):
    user_state[update.message.chat_id] = {}
    await update.message.reply_text("Upload CLOTH image 👕")
    return STAGE_CLOTH


async def get_cloth(update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"cloth_{update.message.chat_id}.png"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["cloth"] = path
    await update.message.reply_text("Now upload MODEL image 👤")
    return STAGE_MODEL


async def get_model(update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"model_{update.message.chat_id}.png"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["model"] = path

    await update.message.reply_text("⏳ Generating try-on image... Please wait 30–45s")

    cloth = open(user_state[update.message.chat_id]["cloth"], "rb").read()
    model_img = open(user_state[update.message.chat_id]["model"], "rb").read()

    try:
        output = client.image_to_image(
            input_image=model_img,
            prompt="apply the cloth realistically on the person, virtual try-on",
            model="ovi054/virtual-tryon-kontext-lora",
            image_guidance=1.1,
            negative_prompt="blur, distortion, wrong hand, artifacts"
        )
    except Exception as e:
        await update.message.reply_text("❌ Error. Try again later.")
        print(e)
        return ConversationHandler.END

    output_bytes = io.BytesIO()
    output.save(output_bytes, format="PNG")
    output_bytes.seek(0)

    await update.message.reply_photo(photo=output_bytes)
    return ConversationHandler.END


conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STAGE_CLOTH: [MessageHandler(filters.PHOTO, get_cloth)],
        STAGE_MODEL: [MessageHandler(filters.PHOTO, get_model)],
    },
    fallbacks=[]
)

application.add_handler(conv)


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    await application.process_update(update)
    return {"ok": True}


@app.get("/")
def home():
    return {"status": "OK"}


@app.on_event("startup")
async def startup():
    await bot.initialize()
    await application.initialize()
    application.bot = bot
    await application.start()
    await bot.set_webhook(WEBHOOK_URL)


@app.on_event("shutdown")
async def shutdown():
    await application.stop()
