import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

STAGE_PRODUCT, STAGE_MODEL = range(2)

user_state = {}

HF_API_URL = "https://api-inference.huggingface.co/models/IDM-VTON/IDM-VTON"

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

async def start(update: Update, context):
    user_state[update.message.chat_id] = {}
    await update.message.reply_text("Upload *PRODUCT image* (T-shirt/Jacket) 📸", parse_mode="Markdown")
    return STAGE_PRODUCT

async def get_product(update: Update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"product_{update.message.chat_id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["product"] = path

    await update.message.reply_text("Now upload *MODEL image* (person photo) 👤", parse_mode="Markdown")
    return STAGE_MODEL

async def get_model(update: Update, context):
    photo = await update.message.photo[-1].get_file()
    path = f"model_{update.message.chat_id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.message.chat_id]["model"] = path

    await update.message.reply_text("⏳ Processing... Please wait 20–40 seconds")

    files = {
        "garment_image": open(user_state[update.message.chat_id]["product"], "rb"),
        "person_image": open(user_state[update.message.chat_id]["model"], "rb"),
    }

    response = requests.post(HF_API_URL, headers=headers, files=files)

    if response.status_code != 200:
        await update.message.reply_text("⚠️ Error: HuggingFace API overloaded or token expired")
        return ConversationHandler.END

    output_url = response.json()["output"]
    await update.message.reply_photo(output_url)

    await update.message.reply_text("✨ Done! Type /start for another try")
    return ConversationHandler.END

app = Application.builder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        STAGE_PRODUCT: [MessageHandler(filters.PHOTO, get_product)],
        STAGE_MODEL: [MessageHandler(filters.PHOTO, get_model)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.run_polling()
