import json
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters
)
from enum import Enum, auto
from dotenv import load_dotenv
from generate import generate_music_from_prompt

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- States ---
class MusicStates(Enum):
    GENRE = auto()
    MOOD = auto()
    TEMPO = auto()
    INSTRUMENT = auto()
    LANGUAGE = auto()
    ERA = auto()
    DESCRIPTION = auto()   # NEW step
    CONFIRM = auto()

# --- Load menu JSON ---
with open("menus.json", "r", encoding="utf-8") as f:
    MENUS = json.load(f)

# --- Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "👋 Welcome to the AI Music Generator Bot!\n\n"
        "With me you can create **custom songs** by choosing:\n"
        "🎼 Genre\n🎭 Mood\n⏱ Tempo\n🎹 Instrument\n🌐 Language\n📅 Era\n📝 Description\n\n"
        "Let's start!\n\n👉 First, pick a *genre*: ",
        parse_mode="Markdown",
        reply_markup=build_keyboard("GENRE")
    )

    return MusicStates.GENRE

# --- Dynamic keyboard generator ---
def build_keyboard(state: str):
    buttons = []
    for row in MENUS[state]["options"]:
        row_buttons = []
        for option in row:
            if option == "Cancel" or "❌" in option:
                row_buttons.append(InlineKeyboardButton(option, callback_data="CANCEL"))
            elif "Confirm" in option or "✅" in option:
                row_buttons.append(InlineKeyboardButton(option, callback_data="CONFIRM"))
            else:
                row_buttons.append(InlineKeyboardButton(option, callback_data=f"{state}:{option}"))
        buttons.append(row_buttons)
    return InlineKeyboardMarkup(buttons)

# --- Handlers ---
async def start_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        MENUS["GENRE"]["message"],
        reply_markup=build_keyboard("GENRE")
    )
    return MusicStates.GENRE

async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, state_key: str, next_state: MusicStates):
    query = update.callback_query
    await query.answer()
    _, choice = query.data.split(":")
    context.user_data[state_key.lower()] = choice

    await query.edit_message_text(
        MENUS[next_state.name]["message"],
        reply_markup=build_keyboard(next_state.name)
    )
    return next_state

# --- Handle ERA → ask description ---
async def handle_era(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, choice = query.data.split(":")
    context.user_data["era"] = choice

    await query.edit_message_text(
        "📝 Now, please type a short description of your song idea.\n\n"
        "For example: *'A calm evening melody with soft piano and gentle rain sounds.'*",
        parse_mode="Markdown"
    )
    return MusicStates.DESCRIPTION

# --- Handle free-text description ---
async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    context.user_data["description"] = description

    summary = (
        f"🎼 *Genre*: {context.user_data.get('genre')}\n"
        f"🎭 *Mood*: {context.user_data.get('mood')}\n"
        f"⏱ *Tempo*: {context.user_data.get('tempo')}\n"
        f"🎹 *Instrument*: {context.user_data.get('instrument')}\n"
        f"🌐 *Language*: {context.user_data.get('language')}\n"
        f"📅 *Era*: {context.user_data.get('era')}\n"
        f"📝 *Description*: {description}\n\n"
        "✅ Confirm to generate your song!"
    )

    await update.message.reply_text(
        summary, parse_mode="Markdown",
        reply_markup=build_keyboard("CONFIRM")
    )
    return MusicStates.CONFIRM

# --- Confirm and generate ---
async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prompt = (
        f"{context.user_data.get('genre')} music, "
        f"{context.user_data.get('mood')} mood, "
        f"{context.user_data.get('tempo')} tempo, "
        f"instrument: {context.user_data.get('instrument')}, "
        f"language: {context.user_data.get('language')}, "
        f"era: {context.user_data.get('era')}. "
        f"Description: {context.user_data.get('description')}"
    )

    await query.edit_message_text(f"🎶 Generating your song:\n\n{prompt}")

    audio_file = generate_music_from_prompt(prompt)

    if audio_file and audio_file.endswith(".mp3"):
        with open(audio_file, "rb") as f:
            await query.message.reply_audio(f, title="🎵 Your AI Generated Song")
    else:
        await query.message.reply_text(f"⚡ This Feature is Coming Soon!")

# --- Cancel handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.edit_message_text("❌ Music generation cancelled.")
    else:
        await update.message.reply_text("❌ Music generation cancelled.")
    return ConversationHandler.END

# --- Conversation Handler ---
music_conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CommandHandler("music", start_music)],
    states={
        MusicStates.GENRE: [CallbackQueryHandler(lambda u, c: handle_selection(u, c, "genre", MusicStates.MOOD), pattern="^GENRE:")],
        MusicStates.MOOD: [CallbackQueryHandler(lambda u, c: handle_selection(u, c, "mood", MusicStates.TEMPO), pattern="^MOOD:")],
        MusicStates.TEMPO: [CallbackQueryHandler(lambda u, c: handle_selection(u, c, "tempo", MusicStates.INSTRUMENT), pattern="^TEMPO:")],
        MusicStates.INSTRUMENT: [CallbackQueryHandler(lambda u, c: handle_selection(u, c, "instrument", MusicStates.LANGUAGE), pattern="^INSTRUMENT:")],
        MusicStates.LANGUAGE: [CallbackQueryHandler(lambda u, c: handle_selection(u, c, "language", MusicStates.ERA), pattern="^LANGUAGE:")],
        MusicStates.ERA: [CallbackQueryHandler(handle_era, pattern="^ERA:")],
        MusicStates.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        MusicStates.CONFIRM: [CallbackQueryHandler(handle_confirm, pattern="^CONFIRM$")],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern="^CANCEL$")],
    allow_reentry=True,
)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(music_conversation_handler)
    print("🚀 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
