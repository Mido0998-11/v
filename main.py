import os
import threading
from flask import Flask
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from engine import SUSTDownloaderEngine

web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Link Extractor Bot Online"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

STEP_USER, STEP_PASS = range(2)
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions:
        await update.message.reply_text("🚀 **البوت جاهز تماماً لتلقي الروابط!**\n\nانسخ رابط أي محاضرة من المنصة (حتى لو روابط pluginfile.php المباشرة) وأرسلها هنا، وسأقوم برفع وتشغيل الفيديو لك داخل تلجرام فوراً.")
    else:
        kb = [['🔐 تسجيل الدخول للحساب']]
        await update.message.reply_text(
            "🔒 **مرحباً بك في بوت SUST لتنزيل المحاضرات المرئية**\n\nبما أن ملفات الفيديو محمية داخل سستم الجامعة، يجب تسجيل دخولك أولاً لمرة واحدة لتفويض البوت بسحب الفيديوهات نيابة عنك.\nاضغط على الزر بالأسفل للبدء.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown'
        )

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 **أرسل الآن الرقم الجامعي الخاص بك:**", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
    return STEP_USER

async def process_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("🔑 **أرسل الآن كلمة المرور الخاصة بك:**\n_(تنبيه: سيتم مسحها فوراً للأمان التام 🛡️)_", parse_mode='Markdown')
    return STEP_PASS

async def process_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['username']
    cid = update.effective_chat.id
    try: await update.message.delete()
    except: pass
    
    status_msg = await update.message.reply_text("⏳ جاري التحقق من الحساب وفتح البوابة الأمنية...")
    engine = SUSTDownloaderEngine()
    
    if engine.login(user, pw):
        user_sessions[cid] = engine
        await context.bot.edit_message_text(
            chat_id=cid, message_id=status_msg.message_id,
            text="✅ **تم تفعيل البوت بنجاح ومطابقة الحساب!**\n\nالآن اذهب للمنصة، انسخ رابط أي محاضرة مرئية (مثل محاضرة الاستاتيكا) وأرسله لي هنا لتشغيلها فوراً.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    else:
        kb = [['🔐 تسجيل الدخول للحساب']]
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text="❌ **بيانات خاطئة!** لم نتمكن من العبور للمنصة. اضغط على الزر وأعد المحاولة.")
        return ConversationHandler.END

async def link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    text = update.message.text

    if cid not in user_sessions:
        kb = [['🔐 تسجيل الدخول للحساب']]
        await update.message.reply_text("🚫 **الوصول مرفوض!** يجب تفعيل البوت وتسجيل دخولك أولاً قبل إرسال الروابط.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return

    if "sustech.edu" not in text:
        await update.message.reply_text("⚠️ هذا الرابط لا يخص منصة جامعة السودان (SUST Moodle).")
        return

    loading = await update.message.reply_text("🔄 جاري الاتصال بالسيرفر ودفق المحاضرة المرئية جوه شات تلجرام... انتظر ثواني...")
    
    try:
        engine = user_sessions[cid]
        # انتزاع الرابط الحقيقي (إذا كان الرابط يحتوي على .mp4 هيرجع زي ما هو فوراً)
        real_video_url = engine.extract_real_video(text)
        
        # فتح اتصال دفق مباشر (Stream) باستخدام الكوكيز حقت الطالب لكسر الحماية
        res = engine.session.get(real_video_url, stream=True, timeout=30)
        cl = res.headers.get('Content-Length')
        size = int(cl) if cl else 0
        
        # إذا كان حجم الفيديو معقول ومناسب لقدرات السيرفر المجاني (أقل من 50 ميجا)
        if 0 < size < 50 * 1024 * 1024:
            await context.bot.send_video(
                chat_id=cid, 
                video=res.raw, # حقن الدفق المباشر في تلجرام دون تخزين في الرام
                filename="lecture.mp4",
                supports_streaming=True, # تشغيل الفيديو لايف أثناء التحميل
                caption="🎬 **تم جلب وتنزيل المحاضرة بنجاح! مشاهدة ممتعة.**", 
                parse_mode='Markdown'
            )
            await loading.delete()
        else:
            # إذا الحجم ضخم جداً، نديه رابط الدفق المباشر يفتح في مشغل التلفون فوراً
            await loading.edit_text(f"ℹ️ حجم هذه المحاضرة كبير جداً ({round(size/(1024*1024), 1)} MB) ويتخطى حد الرفع السريع للبوتات مجاناً. يمكنك تشغيلها وتحميلها فوراً من هذا الرابط المباشر الحصري لحسابك:\n\n🔗 {real_video_url}")
    except Exception as e:
        await loading.edit_text(f"🎥 فشل الدفق التلقائي بسبب جدار حماية السيرفر، لكن يمكنك استخدام رابط التنزيل المباشر المفتوح لحسابك الآن:\n\n🔗 {text}")

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    login_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔐 تسجيل الدخول للحساب$'), login_start)],
        states={
            STEP_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user)],
            STEP_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_pass)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_handler))
    app.run_polling()
