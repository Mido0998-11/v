import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from engine import SUSTEngine

# سيرفر الـ Keep Alive لـ Render
web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Bot is Live"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

# حالات المحادثة خطوة بخطوة
STEP_USER, STEP_PASS = range(2)

# تخزين الجلسات وأسماء الطلاب
user_sessions = {}
user_names = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [['🔐 تسجيل الدخول'], ['📚 مقرراتي الدراسية'], ['🚪 خروج']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome_text = (
        "🎓 **مرحباً بك في منصة جامعة السودان الذكية (SUST)**\n\n"
        "اضغط على زر **'🔐 تسجيل الدخول'** للبدء في ربط حسابك خطوة بخطوة."
    )
    await update.message.reply_text(welcome_text, reply_markup=markup, parse_mode='Markdown')

# --- بداية خطوات تسجيل الدخول ---
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👤 **الخطوة 1:** أرسل الآن **الرقم الجامعي** الخاص بك:", 
        reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown'
    )
    return STEP_USER

async def process_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text(
        "🔑 **الخطوة 2:** أرسل الآن **كلمة المرور** الخاصة بك:\n_(سيتم حذفها تلقائياً فور استلامها لحماية خصوصيتك 🛡️)_",
        parse_mode='Markdown'
    )
    return STEP_PASS

async def process_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['username']
    cid = update.effective_chat.id
    
    # مسح رسالة كلمة المرور فوراً من الشات للأمان
    try: await update.message.delete()
    except: pass
    
    status_msg = await update.message.reply_text("⏳ جاري تسجيل الدخول وفحص الهوية الأكاديمية...")
    
    engine = SUSTEngine()
    if engine.login(user, pw):
        user_sessions[cid] = engine
        
        # جلب البيانات والاسم الرسمي من المنصة
        data = engine.get_profile_and_courses()
        real_name = data['name']
        user_names[cid] = real_name # حفظ الاسم للترحيب به لاحقاً
        
        # الترحيب بالاسم الرسمي المجلوب من الجامعة
        success_text = f"✨ **مرحباً بك، {real_name}**\n\n✅ تم ربط حسابك بالمنصة بنجاح! يمكنك الآن استعراض موادك وفيديوهاتك."
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text=success_text, parse_mode='Markdown')
        
        # إرجاع الكيبورد الرئيسي بعد النجاح
        kb = [['📚 مقرراتي الدراسية'], ['🚪 خروج']]
        await context.bot.send_message(chat_id=cid, text="🗂️ استخدم القائمة أدناه لتصفح محاضراتك:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
    else:
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text="❌ **فشل تسجيل الدخول!**\nالرقم الجامعي أو كلمة المرور غير صحيحة. اضغط على الزر وحاول مجدداً.")
        # إرجاع الكيبورد البدائي لإعادة المحاولة
        kb = [['🔐 تسجيل الدخول']]
        await context.bot.send_message(chat_id=cid, text="🔄 حاول مرة أخرى:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

# --- عرض المواد والملفات ---
async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in user_sessions:
        await update.message.reply_text("⚠️ لم تقم بتسجيل الدخول بعد. اضغط على '🔐 تسجيل الدخول'.")
        return
        
    status = await update.message.reply_text("🔍 جاري جلب مقرراتك الحالية...")
    data = user_sessions[cid].get_profile_and_courses()
    courses = data['courses']
    
    if not courses:
        await status.edit_text("📭 لم نجد مواد نشطة في حسابك حالياً.")
        return
        
    btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
    await status.edit_text("📚 **مقرراتك المسجلة في الجامعة:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        if cid not in user_sessions:
            await query.message.reply_text("⚠️ انتهت الجلسة، يرجى إعادة تسجيل الدخول.")
            return
            
        await query.message.reply_text("🎬 جاري فحص المحاضرات المرئية المتاحة...")
        vids = user_sessions[cid].get_videos(course_id)
        
        if not vids:
            await query.message.reply_text("📭 لا توجد فيديوهات مرفوعة في هذه المادة حالياً.")
            return
            
        for v in vids:
            await context.bot.send_message(chat_id=cid, text=f"🎥 **{v['title']}**\n🔗 {v['url']}", parse_mode='Markdown')

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions: del user_sessions[cid]
    if cid in user_names: del user_names[cid]
    
    kb = [['🔐 تسجيل الدخول']]
    await update.message.reply_text("🔒 تم تسجيل الخروج بنجاح وحذف جلستك الآمنة.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    # هيكلة الـ Conversation Handler لخطوات تسجيل الدخول
    login_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔐 تسجيل الدخول$'), login_start)],
        states={
            STEP_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user)],
            STEP_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_pass)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_wizard)
    app.add_handler(MessageHandler(filters.Regex('^📚 مقرراتي الدراسية$'), show_courses))
    app.add_handler(MessageHandler(filters.Regex('^🚪 خروج$'), logout))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 البوت الدقيق والنظام الخطوي يعمل الآن...")
    app.run_polling()
