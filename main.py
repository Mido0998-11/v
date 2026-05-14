import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SUSTEngine

# --- إعداد سيرفر Flask لـ Render ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot is Running"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- إعدادات البوت ---
TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أزرار الكيبورد الثابتة (Reply Keyboard)
    main_kb = [['📚 موادي', '👤 حسابي'], ['❓ مساعدة']]
    reply_markup = ReplyKeyboardMarkup(main_kb, resize_keyboard=True)
    
    msg = (
        "🎓 **مرحباً بك في منصة SUST الذكية**\n\n"
        "لتصفح موادك، يرجى إرسال بيانات الدخول كالتالي:\n"
        "`الرقم_الجامعي:كلمة_السر`"
    )
    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cid = update.effective_chat.id

    if ":" in text: # معالجة تسجيل الدخول
        user, pw = text.split(":", 1)
        await update.message.reply_text("⏳ جاري الدخول للمنصة...")
        engine = SUSTEngine()
        if engine.login(user, pw):
            user_sessions[cid] = engine
            await update.message.reply_text("✅ تم الدخول بنجاح! يمكنك الآن الضغط على '📚 موادي'.")
        else:
            await update.message.reply_text("❌ فشل الدخول. تأكد من بياناتك.")

    elif text == '📚 موادي':
        if cid not in user_sessions:
            await update.message.reply_text("⚠️ سجل دخولك أولاً.")
            return
        
        await update.message.reply_text("🔄 جاري سحب موادك من المنصة...")
        courses = user_sessions[cid].get_courses()
        
        if not courses:
            await update.message.reply_text("🧐 لا توجد مواد مسجلة.")
            return

        # أزرار مواد متغيرة (Inline Keyboard)
        btns = [[InlineKeyboardButton(c['name'], callback_data=f"c_{c['id']}")] for c in courses]
        await update.message.reply_text("📖 اختر المادة لعرض فيديوهاتها:", reply_markup=InlineKeyboardMarkup(btns))

    elif text == '👤 حسابي':
        status = "متصل ✅" if cid in user_sessions else "غير مسجل ❌"
        await update.message.reply_text(f"👤 **حالة الحساب:** {status}", parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        vids = user_sessions[cid].get_videos(course_id)
        
        if not vids:
            await query.message.reply_text("📭 لا توجد فيديوهات في هذه المادة.")
            return
        
        for v in vids:
            # إرسال روابط الفيديوهات
            await context.bot.send_message(chat_id=cid, text=f"🎥 **{v['title']}**\n🔗 {v['url']}", parse_mode='Markdown')

# --- تشغيل البوت ---
if __name__ == '__main__':
    # تشغيل Flask في خيط منفصل
    threading.Thread(target=run_web).start()
    
    # تشغيل البوت
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 البوت والسيرفر يعملا الآن...")
    app.run_polling()
