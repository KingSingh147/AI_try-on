import os
import requests
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

STAGE_PRODUCT, STAGE_MODEL = range(2)
user_state = {}

HF_API_URL = "https://api-inference.huggingface.co/models/ovi054/virtual-tryon-kontext-lora"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

bot = Bot(TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).updater(None).build()

app = FastAPI()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_chat.id] = {}
    await update.message.reply_text("📌 Step 1: Upload the CLOTH image")
    return STAGE_PRODUCT


async def get_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    path = f"cloth_{update.effective_chat.id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.effective_chat.id]["cloth"] = path
    await update.message.reply_text("📌 Step 2: Upload the MODEL image")
    return STAGE_MODEL


async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    path = f"model_{update.effective_chat.id}.jpg"
    await photo.download_to_drive(path)
    user_state[update.effective_chat.id]["model"] = path
    await update.message.reply_text("⏳ Generating result… Please wait 30–60 sec.")

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
    fallbacks=[]
)
application.add_handler(conv)


# ---------- WEBHOOK ----------
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
    return {"status": "BOT RUNNING"}
    

@app.on_event("startup")
async def startup():
    await application.initialize()
    await bot.set_webhook(f"{os.getenv('WEBHOOK_URL')}/webhook/{TELEGRAM_TOKEN}")
    await application.start()
