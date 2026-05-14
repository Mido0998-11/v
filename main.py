import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from engine import SUSTEngine

# --- إعدادات Flask لـ Render ---
web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Bot is Live!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- ثوابت المحادثة ---
CHOOSING, TYPING_USER, TYPING_PASS = range(3)
TOKEN = os.environ.get('BOT_TOKEN') # اسحب التوكن من رندر

user_sessions = {}

# --- دوال البوت ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_kb = [['🔐 تسجيل الدخول'], ['📚 مقرراتي الدراسية'], ['👤 حسابي', '🚪 خروج']]
    markup = ReplyKeyboardMarkup(reply_kb, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎓 **مرحباً بك في منصة SUST الذكية**\n\nأنا مساعدك الرقمي للوصول لمحاضراتك وفيديوهاتك بسرعة.\nاختر من القائمة أدناه للبدء.",
        reply_markup=markup, parse_mode='Markdown'
    )

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 يرجى إرسال **الرقم الجامعي** الخاص بك:", parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
    return TYPING_USER

async def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_user'] = update.message.text
    await update.message.reply_text("🔑 الآن أرسل **كلمة المرور**:\n(سيتم مسحها تلقائياً للأمان 🛡️)", parse_mode='Markdown')
    return TYPING_PASS

async def get_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['temp_user']
    cid = update.effective_chat.id
    
    # مسح رسالة الباسورد للأمان
    try: await update.message.delete()
    except: pass

    status_msg = await update.message.reply_text("⏳ **جاري التحقق من بياناتك في المنصة...**", parse_mode='Markdown')
    
    engine = SUSTEngine()
    if engine.login(user, pw):
        user_sessions[cid] = engine
        await context.bot.edit_message_text(
            chat_id=cid, message_id=status_msg.message_id,
            text="✅ **تم تسجيل الدخول بنجاح!**\nيمكنك الآن تصفح محاضراتك من القائمة.",
            parse_mode='Markdown'
        )
        # إعادة الكيبورد الرئيسي
        await start(update, context)
    else:
        await context.bot.edit_message_text(
            chat_id=cid, message_id=status_msg.message_id,
            text="❌ **بيانات خاطئة!**\nيرجى المحاولة مرة أخرى بالضغط على زر الدخول."
        )
    return ConversationHandler.END

async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in user_sessions:
        await update.message.reply_text("⚠️ يرجى تسجيل الدخول أولاً باستخدام زر '🔐 تسجيل الدخول'.")
        return

    wait = await update.message.reply_text("🔄 جاري سحب قائمة المواد...")
    courses = user_sessions[cid].get_courses()
    
    if not courses:
        await wait.edit_text("🧐 لم أجد مواد مسجلة حالياً.")
        return

    btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
    await wait.edit_text("📚 **مقرراتك الدراسية:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        vids = user_sessions[cid].get_videos(course_id)
        
        if not vids:
            await query.message.reply_text("📭 لا توجد فيديوهات مرفوعة في هذه المادة.")
            return
        
        for v in vids:
            await context.bot.send_message(chat_id=cid, text=f"🎬 **{v['title']}**\n🔗 [رابط الفيديو المباشر]({v['url']})", parse_mode='Markdown')

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions: del user_sessions[cid]
    await update.message.reply_text("👋 تم تسجيل الخروج بنجاح. نراك لاحقاً!")

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # معالج المحادثة الاحترافي لتسجيل الدخول
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔐 تسجيل الدخول$'), login_start)],
        states={
            TYPING_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user)],
            TYPING_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pass)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex('^📚 مقرراتي الدراسية$'), show_courses))
    app.add_handler(MessageHandler(filters.Regex('^🚪 خروج$'), logout))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 المنصة الاحترافية تعمل الآن...")
    app.run_polling()
