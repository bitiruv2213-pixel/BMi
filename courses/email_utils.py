from django.core.mail import send_mail
from django.conf import settings

SITE_URL = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')


def send_welcome_email(user):
    """Yangi foydalanuvchiga xush kelibsiz email"""
    subject = 'LMS Platformaga xush kelibsiz!'
    message = f'''
Salom {user.get_full_name()}!

LMS Platformaga xush kelibsiz!

Sizning akkauntingiz muvaffaqiyatli yaratildi.

Username: {user.username}

Kurslarni ko'rish: {SITE_URL}/courses/

Rahmat,
LMS Team
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@lms.com',
            [user.email],
            fail_silently=True,
        )
    except:
        pass


def send_enrollment_email(enrollment):
    """Kursga yozilganda email"""
    user = enrollment.student
    course = enrollment.course

    subject = f'Siz "{course.title}" kursiga yozildingiz!'
    message = f'''
Salom {user.get_full_name()}!

Tabriklaymiz! Siz "{course.title}" kursiga muvaffaqiyatli yozildingiz.

Kurs haqida:
- O'qituvchi: {course.teacher.get_full_name()}
- Darslar soni: {course.total_lessons} ta

O'qishni boshlash: {SITE_URL}/courses/{course.slug}/learn/

Omad tilaymiz!

LMS Team
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@lms.com',
            [user.email],
            fail_silently=True,
        )
    except:
        pass


def send_certificate_email(certificate):
    """Sertifikat berilganda email"""
    user = certificate.student
    course = certificate.course

    subject = 'Tabriklaymiz! Sertifikat oldingiz!'
    message = f'''
Salom {user.get_full_name()}!

Tabriklaymiz! Siz "{course.title}" kursini muvaffaqiyatli tugatdingiz!

Sertifikat ma'lumotlari:
- Sertifikat raqami: {certificate.certificate_number}
- Berilgan sana: {certificate.issued_at.strftime('%d.%m.%Y')}

Sertifikatni ko'rish: {SITE_URL}/certificates/{certificate.id}/

Yangi yutuqlar tilaymiz!

LMS Team
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@lms.com',
            [user.email],
            fail_silently=True,
        )
    except:
        pass


def send_grade_notification(submission):
    """Baho qo'yilganda email"""
    user = submission.student
    assignment = submission.assignment

    subject = 'Topshiriqingiz baholandi!'
    message = f'''
Salom {user.get_full_name()}!

"{assignment.title}" topshirig'ingiz baholandi.

Natija: {submission.score}/{assignment.max_score} ball

Izoh: {submission.feedback or "Izoh yo'q"}

LMS Team
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@lms.com',
            [user.email],
            fail_silently=True,
        )
    except:
        pass


def send_quiz_result_email(attempt):
    """Quiz natijasi email"""
    user = attempt.student
    quiz = attempt.quiz

    status_text = "muvaffaqiyatli o'tdingiz" if attempt.passed else "o'ta olmadingiz"

    subject = f'Quiz natijasi: {quiz.title}'
    message = f'''
Salom {user.get_full_name()}!

"{quiz.title}" quiz natijasi:

Ball: {attempt.score:.0f}%
Holat: Siz {status_text}
To'g'ri javoblar: {attempt.correct_count}
Noto'g'ri javoblar: {attempt.wrong_count}
Qo'shilgan XP: +{attempt.xp_earned}

LMS Team
    '''

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@lms.com',
            [user.email],
            fail_silently=True,
        )
    except:
        pass
