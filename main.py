import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from engine import SUSTEngine

# سيرفر الـ Keep Alive لـ Render
web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Bot Operational"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

# سنستخدم نظام تخزين مرن للجلسات لتفادي كراش الأزرار
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [['📚 مقرراتي الدراسية'], ['🚪 تسجيل خروج']]
    markup = ReplyKeyboardMarkup(kb, resize_keyboard=True)
    
    welcome = (
        "🎓 **منصة جامعة السودان الذكية (SUST)**\n\n"
        "الرجاء إرسال بياناتك لتسجيل الدخول بشكل مباشر بالصيغة التالية:\n"
        "`الرقم_الجامعي:كلمة_المرور`\n\n"
        "🔒 _سيتم تشفير البيانات وحذف الرسالة فوراً للأمان._"
    )
    await update.message.reply_text(welcome, reply_markup=markup, parse_mode='Markdown')

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    cid = update.effective_chat.id

    # حالة تسجيل الدخول
    if ":" in text:
        user, pw = text.split(":", 1)
        # مسح رسالة الباسورد فوراً
        try: await update.message.delete()
        except: pass
        
        status = await update.message.reply_text("⏳ جاري الاتصال بالسيرفر الرئيسي للجامعة...")
        
        engine = SUSTEngine()
        if engine.login(user, pw):
            user_sessions[cid] = engine  # حفظ الجلسة في الرام
            await status.edit_text("✅ **تم تسجيل الدخول بنجاح!**\nاضغط الآن على زر '📚 مقرراتي الدراسية' بالأسفل.", parse_mode='Markdown')
        else:
            await status.edit_text("❌ **فشل الدخول!**\nتأكد من الرقم السري أو الحساب وأرسلهما مجدداً بصيغة `user:pass`")

    elif text == '📚 مقرراتي الدراسية':
        if cid not in user_sessions:
            await update.message.reply_text("⚠️ انتهت جلستك أو لم تسجل دخولك بعد. أرسل بياناتك أولاً بصيغة `user:pass`")
            return
        
        status = await update.message.reply_text("🔍 جاري قراءة ملفك الأكاديمي وسحب المواد...")
        courses = user_sessions[cid].get_courses()
        
        if not courses:
            await status.edit_text("🧐 تم الدخول، ولكن لم نجد مواد في بروفايلك أو أن المنصة تواجه ضغطاً.")
            return
            
        btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
        await status.edit_text("👇 **اختر المادة لعرض محاضراتها:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif text == '🚪 تسجيل خروج':
        if cid in user_sessions: del user_sessions[cid]
        await update.message.reply_text("تم تسجيل الخروج بنجاح 🔒")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        if cid not in user_sessions:
            await query.message.reply_text("⚠️ انتهت الجلسة، يرجى إعادة إرسال بيانات الدخول.")
            return
            
        await query.message.reply_text("🎬 جاري فحص الفيديوهات المتاحة المحاضرة...")
        vids = user_sessions[cid].get_videos(course_id)
        
        if not vids:
            await query.message.reply_text("📭 لا توجد فيديوهات مرفوعة في هذه المادة حالياً.")
            return
            
        for v in vids:
            await context.bot.send_message(chat_id=cid, text=f"🎥 **{v['title']}**\n🔗 {v['url']}", parse_mode='Markdown')

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("🚀 البوت المطور والدقيق يعمل الآن...")
    app.run_polling()
