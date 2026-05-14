import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SUSTEngine

# ضع التوكن هنا (أو استخدم بيئة العمل)
TOKEN = '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s'

user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [['📚 موادي', '👤 حسابي'], ['❓ مساعدة']]
    await update.message.reply_text(
        "👋 **أهلاً بك في منصة SUST الذكية**\nارسل بياناتك كالتالي لتسجيل الدخول:\n`الرقم:كلمة_السر`",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cid = update.effective_chat.id

    if ":" in text:
        user, pw = text.split(":", 1)
        engine = SUSTEngine()
        await update.message.reply_text("⏳ جاري التحقق من المنصة...")
        if engine.login(user, pw):
            user_sessions[cid] = engine
            await update.message.reply_text("✅ تم الدخول! اضغط '📚 موادي' الآن.")
        else:
            await update.message.reply_text("❌ خطأ في البيانات.")

    elif text == '📚 موادي':
        if cid not in user_sessions:
            await update.message.reply_text("⚠️ سجل دخولك أولاً.")
            return
        courses = user_sessions[cid].get_courses()
        btns = [[InlineKeyboardButton(c['name'], callback_data=f"c_{c['id']}")] for c in courses]
        await update.message.reply_text("📖 اختر المادة:", reply_markup=InlineKeyboardMarkup(btns))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        vids = user_sessions[cid].get_videos(course_id)
        if not vids:
            await query.edit_message_text("🧐 لا توجد فيديوهات في هذه المادة.")
            return
        
        for v in vids:
            await context.bot.send_message(chat_id=cid, text=f"🎥 {v['title']}\n🔗 {v['url']}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()
