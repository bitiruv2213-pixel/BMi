import asyncio
from telegram import Bot
from django.conf import settings

BOT_TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')


async def send_telegram_message_async(telegram_id, message):
    '''Telegram ga xabar yuborish'''
    if not BOT_TOKEN:
        return False
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=telegram_id, text=message, parse_mode='Markdown')
        return True
    except Exception as e:
        print(f'Telegram xatolik: {e}')
        return False


def send_telegram_message(telegram_id, message):
    '''Sinxron wrapper'''
    return asyncio.run(send_telegram_message_async(telegram_id, message))


def notify_course_enrollment(enrollment):
    '''Kursga yozilganda xabar'''
    try:
        tg_user = enrollment.student.telegram
        if tg_user.notifications_enabled:
            message = f'''
🎉 *Tabriklaymiz!*

Siz \\"{enrollment.course.title}\\" kursiga yozildingiz!

👨‍🏫 O'qituvchi: {enrollment.course.teacher.get_full_name()}
📚 Darslar: {enrollment.course.total_lessons} ta

O'qishni boshlang! 🚀
            '''
            send_telegram_message(tg_user.telegram_id, message)
    except:
        pass


def notify_lesson_complete(student, lesson):
    '''Dars tugatilganda xabar'''
    try:
        tg_user = student.telegram
        if tg_user.notifications_enabled:
            message = f'''
✅ *Dars tugatildi!*

\\"{lesson.title}\\" darsi muvaffaqiyatli tugatildi.

⭐ +{lesson.xp_reward} XP qo'shildi!
            '''
            send_telegram_message(tg_user.telegram_id, message)
    except:
        pass


def notify_certificate_issued(certificate):
    '''Sertifikat berilganda xabar'''
    try:
        tg_user = certificate.student.telegram
        if tg_user.notifications_enabled:
            message = f'''
🏆 *Tabriklaymiz!*

\\"{certificate.course.title}\\" kursi bo'yicha sertifikat oldingiz!

📜 Sertifikat raqami: {certificate.certificate_number}
            '''
            send_telegram_message(tg_user.telegram_id, message)
    except:
        pass
