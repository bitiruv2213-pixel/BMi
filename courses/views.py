from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from django.conf import settings
from accounts.role_utils import get_role, is_teacher, is_supervisor, is_admin
from .certificate_generator import CertificateGenerator
from .models import (
    Category, Course, Lesson, Enrollment, LessonProgress,
    Quiz, Question, Answer, QuizAttempt, QuizResponse,
    Assignment, Submission, Certificate, CourseReview,
    Discussion, Reply, Notification, Payment, PromoCode,
    Wishlist, Badge, UserBadge, UserXP, XPTransaction,
    DailyChallenge, UserChallenge, AIGradeRecommendation,
    TypingText, CodeChallenge, GameScore, MemoryCard
)
from .forms import (
    CourseForm, LessonForm, QuizForm, QuestionForm,
    AssignmentForm, SubmissionForm, ReviewForm,
    DiscussionForm, ReplyForm
)

# AI import
import requests as _requests
AI_AVAILABLE = True


QUIZ_REQUIRED_QUESTION_COUNT = 10
QUIZ_REQUIRED_PASS_SCORE = 75
QUIZ_REQUIRED_MAX_ATTEMPTS = 3
QUIZ_FAILED_XP_PENALTY = 10

GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _call_gemini(parts, timeout=30):
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return {
            'ok': False,
            'error_type': 'missing_key',
            'message': "AI kaliti sozlanmagan.",
        }

    try:
        resp = _requests.post(
            GEMINI_GENERATE_URL,
            params={"key": api_key},
            json={"contents": [{"parts": parts}]},
            timeout=timeout,
        )
        try:
            data = resp.json()
        except ValueError:
            data = {}

        if resp.status_code == 200:
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            if text:
                return {'ok': True, 'text': text, 'data': data}
            return {
                'ok': False,
                'error_type': 'empty_response',
                'message': "AI bo'sh javob qaytardi.",
                'data': data,
            }

        error = data.get("error", {}) if isinstance(data, dict) else {}
        error_message = error.get("message", "Noma'lum xatolik")
        error_status = str(error.get("status", "")).upper()

        is_quota_error = (
            resp.status_code == 429
            or error_status in {'RESOURCE_EXHAUSTED', 'RATE_LIMIT_EXCEEDED'}
            or 'quota' in error_message.lower()
            or 'billing' in error_message.lower()
        )

        return {
            'ok': False,
            'error_type': 'quota' if is_quota_error else 'api',
            'message': error_message,
            'status_code': resp.status_code,
            'data': data,
        }
    except _requests.RequestException as exc:
        return {
            'ok': False,
            'error_type': 'network',
            'message': str(exc),
        }
    except Exception as exc:
        return {
            'ok': False,
            'error_type': 'unexpected',
            'message': str(exc),
        }


def _build_fallback_ai_grade(submission, assignment, reason):
    max_score = assignment.max_score or 100
    submission_text = (submission.content or '').strip()
    has_file = bool(submission.file)

    content_length = len(submission_text)
    ratio = 0.35
    if content_length >= 120:
        ratio = 0.55
    if content_length >= 400:
        ratio = 0.7
    if has_file:
        ratio += 0.1

    ratio = min(ratio, 0.85)
    score = max(0, min(max_score, int(round(max_score * ratio))))

    return {
        'score': score,
        'confidence': 0.35,
        'analysis': (
            "AI servis vaqtincha ishlamadi, shuning uchun taxminiy fallback tahlil yaratildi. "
            f"Sabab: {reason[:120]}"
        ),
        'strengths': "Topshiriq avtomatik tarzda to'liq tahlil qilinmadi.",
        'weaknesses': "Natija Gemini quota yoki tarmoq cheklovi sabab cheklangan.",
        'suggestions': "Admin AI kalitini yoki billing/quota holatini tekshirsin; o'qituvchi qo'lda review qilsin.",
    }


def _clamp_int(value, default, *, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _clamp_float(value, default, *, minimum=None, maximum=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default

    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _parse_bounded_score(value, maximum):
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(maximum, score))


def _read_text_file(file_path, max_chars=8000):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as fh:
        return fh.read(max_chars)


def _extract_docx_text(file_path, max_chars=8000):
    import zipfile
    from xml.etree import ElementTree as ET

    with zipfile.ZipFile(file_path) as archive:
        xml_bytes = archive.read('word/document.xml')

    root = ET.fromstring(xml_bytes)
    text_nodes = [node.text for node in root.iter() if node.tag.endswith('}t') and node.text]
    return ' '.join(text_nodes)[:max_chars]


def _extract_pptx_text(file_path, max_chars=8000):
    import zipfile
    from xml.etree import ElementTree as ET

    collected = []
    with zipfile.ZipFile(file_path) as archive:
        slide_names = sorted(
            name for name in archive.namelist()
            if name.startswith('ppt/slides/slide') and name.endswith('.xml')
        )
        for slide_name in slide_names:
            root = ET.fromstring(archive.read(slide_name))
            slide_text = [node.text for node in root.iter() if node.tag.endswith('}t') and node.text]
            if slide_text:
                collected.append(' '.join(slide_text))

    return '\n'.join(collected)[:max_chars]


def _extract_xlsx_text(file_path, max_chars=8000):
    import zipfile
    from xml.etree import ElementTree as ET

    def _cell_value(cell, shared_strings):
        cell_type = cell.attrib.get('t')
        value_node = next((child for child in cell if child.tag.endswith('}v') and child.text), None)
        if value_node is None:
            return ''
        raw_value = value_node.text or ''
        if cell_type == 's':
            try:
                return shared_strings[int(raw_value)]
            except (ValueError, IndexError):
                return raw_value
        return raw_value

    shared_strings = []
    rows = []
    with zipfile.ZipFile(file_path) as archive:
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared_root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            for string_item in shared_root.iter():
                if string_item.tag.endswith('}t') and string_item.text:
                    shared_strings.append(string_item.text)

        sheet_names = sorted(
            name for name in archive.namelist()
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')
        )
        for sheet_name in sheet_names:
            root = ET.fromstring(archive.read(sheet_name))
            for row in root.iter():
                if not row.tag.endswith('}row'):
                    continue
                values = []
                for cell in row:
                    if cell.tag.endswith('}c'):
                        value = _cell_value(cell, shared_strings)
                        if value:
                            values.append(value)
                if values:
                    rows.append(' | '.join(values))

    return '\n'.join(rows)[:max_chars]


def _build_inline_file_part(file_path, mime_type):
    import base64 as _base64
    import os as _os

    file_size = _os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:
        return None, "[Fayl juda katta, AI inline tahliliga yuborilmadi]"

    with open(file_path, 'rb') as fh:
        encoded = _base64.b64encode(fh.read()).decode('utf-8')
    return {"inline_data": {"mime_type": mime_type, "data": encoded}}, None


def _extract_file_for_ai(field_file, role_label, max_chars=8000):
    import os as _os

    if not field_file:
        return {'text': '', 'parts': [], 'notes': []}

    file_path = field_file.path
    file_name = _os.path.basename(file_path)
    file_ext = _os.path.splitext(file_name)[1].lower()

    text_extensions = {
        '.py', '.txt', '.js', '.ts', '.html', '.css', '.java',
        '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs',
        '.md', '.json', '.xml', '.csv', '.sql', '.sh', '.yaml', '.yml',
    }
    office_text_extractors = {
        '.docx': _extract_docx_text,
        '.pptx': _extract_pptx_text,
        '.xlsx': _extract_xlsx_text,
    }
    inline_mime = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }

    try:
        if file_ext in text_extensions:
            file_content = _read_text_file(file_path, max_chars=max_chars)
            return {
                'text': f"\n\n--- {role_label} fayli: {file_name} ---\n{file_content}",
                'parts': [],
                'notes': [],
            }

        if file_ext in office_text_extractors:
            file_content = office_text_extractors[file_ext](file_path, max_chars=max_chars)
            return {
                'text': f"\n\n--- {role_label} fayli: {file_name} ---\n{file_content}",
                'parts': [],
                'notes': [],
            }

        if file_ext in inline_mime:
            inline_part, note = _build_inline_file_part(file_path, inline_mime[file_ext])
            notes = [f"{role_label} fayli AI inline tahlilga yuborildi: {file_name}"]
            if note:
                return {'text': f"\n\n[{role_label} fayli inline yuborilmadi: {file_name}]", 'parts': [], 'notes': [note]}
            return {'text': '', 'parts': [inline_part], 'notes': notes}

        return {
            'text': f"\n\n[{role_label} fayli turi hozircha to'liq qo'llab-quvvatlanmaydi: {file_name}]",
            'parts': [],
            'notes': [],
        }
    except Exception as exc:
        return {
            'text': f"\n\n[{role_label} faylini o'qishda xatolik: {file_name}]",
            'parts': [],
            'notes': [str(exc)],
        }


def _fallback_chat_response(message, course=None, error_type=None):
    course_text = f" '{course.title}' kursi bo'yicha" if course else ''
    guidance = (
        "AI xizmatida vaqtinchalik cheklov bor. "
        "Shu sabab avtomatik javob o'rniga qisqa yo'l-yo'riq beraman.\n\n"
    )
    if error_type == 'missing_key':
        guidance = (
            "AI xizmati hali sozlanmagan. "
            "Admin `GEMINI_API_KEY` ni yangilashi kerak.\n\n"
        )

    lower_message = message.lower()

    if 'django' in lower_message:
        body = (
            f"Django{course_text} bo'yicha tavsiya:\n"
            "1. `urls.py`, `views.py`, `templates/` bog'lanishini tekshiring.\n"
            "2. Model o'zgargan bo'lsa `makemigrations` va `migrate` qiling.\n"
            "3. Form yoki query xatosida traceback'ning eng past qatorini tekshiring.\n"
            "4. Xatolik matnini yuborsangiz, aniqroq yechim beraman."
        )
    elif 'python' in lower_message:
        body = (
            f"Python{course_text} bo'yicha tavsiya:\n"
            "1. Masalani kichik funksiyalarga bo'ling.\n"
            "2. `print()` yoki debugger bilan oraliq qiymatlarni tekshiring.\n"
            "3. `TypeError`, `KeyError`, `IndexError` bo'lsa kiruvchi ma'lumotni tekshiring.\n"
            "4. Kod bo'lagini yuborsangiz, to'g'ridan-to'g'ri tuzatib beraman."
        )
    elif 'xato' in lower_message or 'error' in lower_message:
        body = (
            "Xatoni topish uchun quyidagilarni yuboring:\n"
            "1. To'liq error matni\n"
            "2. Shu xatoga olib kelgan kod bo'lagi\n"
            "3. Qaysi fayl va qaysi amal paytida chiqqani\n"
            "Shunda aniq yechim yozaman."
        )
    else:
        body = (
            f"Savolingiz{course_text} bo'yicha qabul qilindi, lekin AI servis hozir limitga urildi.\n"
            "Savolni aniqroq yozing yoki kod/error parchani yuboring. "
            "Men mavjud ma'lumot asosida qo'lda yo'naltiruvchi javob beraman."
        )

    return guidance + body


def _redirect_dashboard_for_role(request):
    role = get_role(request.user)
    if role == 'admin':
        return redirect('admin:index')
    if role == 'supervisor':
        return redirect('supervisor_dashboard')
    if role == 'teacher':
        return redirect('teacher_dashboard')
    return None


def _require_teacher(request):
    if not is_teacher(request.user):
        messages.error(request, "Bu sahifa faqat o'qituvchilar uchun!")
        return False
    return True


def _require_supervisor(request):
    if not (is_supervisor(request.user) or is_admin(request.user)):
        messages.error(request, "Sizda ruxsat yo'q!")
        return False
    return True


def _require_student(request):
    if get_role(request.user) != 'student':
        messages.error(request, "Bu sahifa faqat talabalar uchun!")
        return False
    return True


def _require_ai_mentor_access(request):
    if is_teacher(request.user) or is_admin(request.user):
        return True
    messages.error(request, "AI Mentor faqat o'qituvchi va admin uchun mavjud.")
    return False


# ==========================================
# HOME
# ==========================================
def home(request):
    featured_courses = Course.objects.filter(is_published=True, is_featured=True)[:6]
    categories = Category.objects.filter(is_active=True)[:8]
    total_courses = Course.objects.filter(is_published=True).count()
    total_students = Enrollment.objects.values('student_id').distinct().count()
    total_teachers = User.objects.filter(
        profile__is_teacher=True,
        courses_teaching__is_published=True
    ).distinct().count()

    approved_reviews = CourseReview.objects.filter(is_approved=True)
    review_count = approved_reviews.count()
    satisfaction_rate = 0
    if review_count:
        satisfaction_rate = round(
            approved_reviews.filter(rating__gte=4).count() * 100 / review_count
        )

    context = {
        'featured_courses': featured_courses,
        'categories': categories,
        'platform_stats': {
            'total_courses': total_courses,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'satisfaction_rate': satisfaction_rate,
        }
    }
    return render(request, 'home.html', context)


# ==========================================
# DASHBOARD (Student)
# ==========================================
@login_required
def dashboard(request):
    redirect_response = _redirect_dashboard_for_role(request)
    if redirect_response:
        return redirect_response

    user = request.user
    enrollments = Enrollment.objects.filter(student=user).select_related('course')

    xp_profile, _ = UserXP.objects.get_or_create(user=user)
    recent_activities = XPTransaction.objects.filter(user=user).order_by('-created_at')[:5]
    certificates = Certificate.objects.filter(student=user).order_by('-issued_at')[:3]
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')[:6]

    enrolled_course_ids = enrollments.values_list('course_id', flat=True)
    recommended_courses = Course.objects.filter(
        is_published=True
    ).exclude(id__in=enrolled_course_ids).order_by('-created_at')[:4]

    completed_count = enrollments.filter(completed=True).count()
    in_progress_count = enrollments.filter(completed=False).count()

    context = {
        'enrollments': enrollments[:6],
        'xp_profile': xp_profile,
        'recent_activities': recent_activities,
        'certificates': certificates,
        'user_badges': user_badges,
        'recommended_courses': recommended_courses,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'total_courses': enrollments.count(),
    }
    return render(request, 'courses/dashboard.html', context)


# ==========================================
# COURSE LIST & DETAIL
# ==========================================
def course_list(request):
    if request.user.is_authenticated:
        role = get_role(request.user)
        if role == 'teacher':
            messages.info(request, "Siz o'qituvchisiz. O'qituvchi paneliga o'tdingiz.")
            return redirect('teacher_dashboard')
        if role == 'supervisor':
            messages.info(request, "Siz nazoratchisiz. Nazoratchi paneliga o'tdingiz.")
            return redirect('supervisor_dashboard')
        if role == 'admin':
            return redirect('admin:index')

    courses = Course.objects.filter(is_published=True).select_related('teacher', 'category')
    categories = Category.objects.filter(is_active=True).annotate(course_count=Count('courses'))

    query = request.GET.get('q')
    if query:
        courses = courses.filter(Q(title__icontains=query) | Q(description__icontains=query))

    category_slug = request.GET.get('category')
    if category_slug:
        courses = courses.filter(category__slug=category_slug)

    level = request.GET.get('level')
    if level:
        courses = courses.filter(level=level)

    is_free = request.GET.get('free')
    if is_free:
        courses = courses.filter(is_free=True)

    sort = request.GET.get('sort', '-created_at')
    if sort == 'popular':
        courses = courses.order_by('-total_students')
    elif sort == 'rating':
        courses = courses.order_by('-average_rating')
    elif sort == 'price_low':
        courses = courses.order_by('price')
    elif sort == 'price_high':
        courses = courses.order_by('-price')
    else:
        courses = courses.order_by('-created_at')

    paginator = Paginator(courses, 12)
    page = request.GET.get('page')
    courses = paginator.get_page(page)

    context = {
        'courses': courses,
        'categories': categories,
        'current_category': category_slug,
        'current_level': level,
        'current_sort': sort,
        'query': query,
    }
    return render(request, 'courses/course_list.html', context)


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    lessons = course.lessons.filter(is_published=True).order_by('order')
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')[:10]

    is_enrolled = False
    enrollment = None
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(student=request.user, course=course).first()
        is_enrolled = enrollment is not None

    related_courses = Course.objects.filter(
        category=course.category, is_published=True
    ).exclude(id=course.id)[:4]

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, course=course).exists()

    context = {
        'course': course,
        'lessons': lessons,
        'reviews': reviews,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
        'related_courses': related_courses,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'courses/course_detail.html', context)


# ==========================================
# ENROLLMENT
# ==========================================
@login_required
def enroll_course(request, slug):
    if not _require_student(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.info(request, "Siz allaqachon bu kursga yozilgansiz!")
        return redirect('course_learn', slug=slug)

    if course.is_free:
        Enrollment.objects.create(student=request.user, course=course)
        course.total_students += 1
        course.save()
        messages.success(request, f"'{course.title}' kursiga muvaffaqiyatli yozildingiz!")
        return redirect('course_learn', slug=slug)

    return redirect('payment_checkout', slug=slug)


@login_required
def my_courses(request):
    if not _require_student(request):
        return redirect('dashboard')

    enrollments = Enrollment.objects.filter(student=request.user).select_related('course')

    status = request.GET.get('status')
    if status == 'completed':
        enrollments = enrollments.filter(completed=True)
    elif status == 'in_progress':
        enrollments = enrollments.filter(completed=False)

    context = {
        'enrollments': enrollments,
        'current_status': status,
    }
    return render(request, 'courses/my_courses.html', context)


# ==========================================
# LEARNING
# ==========================================
def _apply_quiz_failure_penalty(student, quiz):
    """3 urinishdan o'ta olmagan talabaga bir marta XP jarima qo'llash."""
    penalty_description = f"Quiz penalty #{quiz.id} (3 failed attempts)"
    already_penalized = XPTransaction.objects.filter(
        user=student,
        amount=-QUIZ_FAILED_XP_PENALTY,
        description=penalty_description
    ).exists()

    if already_penalized:
        return

    xp_profile, _ = UserXP.objects.get_or_create(user=student)
    xp_profile.add_xp(-QUIZ_FAILED_XP_PENALTY, penalty_description)


def _get_lesson_gate_status(student, lesson):
    """Darsni tugatish uchun talab etilgan test/topshiriq holati."""
    reasons = []

    quiz = Quiz.objects.filter(lesson=lesson, is_active=True).order_by('created_at').first()
    if not quiz:
        reasons.append("Bu mavzu uchun test yaratilmagan.")
    else:
        question_count = quiz.questions.count()
        if question_count < QUIZ_REQUIRED_QUESTION_COUNT:
            reasons.append(
                f"Testda kamida {QUIZ_REQUIRED_QUESTION_COUNT} ta savol bo'lishi kerak (hozir: {question_count})."
            )
        attempts = QuizAttempt.objects.filter(student=student, quiz=quiz)
        passed_quiz = attempts.filter(score__gte=QUIZ_REQUIRED_PASS_SCORE).exists()
        if not passed_quiz:
            attempts_count = attempts.count()
            if attempts_count >= QUIZ_REQUIRED_MAX_ATTEMPTS:
                reasons.append("Testdan o'tish urinishlari tugagan (3/3).")
            else:
                reasons.append(
                    f"Testdan kamida {QUIZ_REQUIRED_PASS_SCORE}% natija bilan o'tish kerak "
                    f"({attempts_count}/{QUIZ_REQUIRED_MAX_ATTEMPTS} urinish ishlatilgan)."
                )

    assignments = Assignment.objects.filter(lesson=lesson)
    if not assignments.exists():
        reasons.append("Bu mavzu uchun topshiriq yaratilmagan.")
    else:
        submitted_count = Submission.objects.filter(
            student=student, assignment__in=assignments
        ).values('assignment_id').distinct().count()
        if submitted_count < assignments.count():
            reasons.append(
                f"Barcha topshiriqlarni yuklash kerak ({submitted_count}/{assignments.count()})."
            )

    return {
        'can_complete': len(reasons) == 0,
        'reasons': reasons,
    }


@login_required
def course_learn(request, slug):
    if not _require_student(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)
    lessons = list(course.lessons.filter(is_published=True).order_by('order'))
    completed_lessons = set(LessonProgress.objects.filter(
        student=request.user, lesson__course=course, completed=True
    ).values_list('lesson_id', flat=True))

    accessible_lessons = []
    lock_next = False
    for lesson in lessons:
        if lock_next:
            continue
        accessible_lessons.append(lesson.id)
        if lesson.id not in completed_lessons:
            lock_next = True

    current_lesson = None
    current_lesson_id = request.GET.get('lesson')
    if current_lesson_id:
        try:
            current_lesson_id = int(current_lesson_id)
        except (TypeError, ValueError):
            current_lesson_id = None
        if current_lesson_id in accessible_lessons:
            current_lesson = next((lesson for lesson in lessons if lesson.id == current_lesson_id), None)
        elif current_lesson_id:
            messages.warning(request, "Oldingi mavzuni tugatmaguningizcha keyingi mavzuga o'ta olmaysiz.")

    if current_lesson is None and lessons:
        current_lesson = next((lesson for lesson in lessons if lesson.id in accessible_lessons and lesson.id not in completed_lessons), None)
        if current_lesson is None:
            current_lesson = lessons[0]

    current_lesson_gate = _get_lesson_gate_status(request.user, current_lesson) if current_lesson else None
    submitted_assignment_ids = []
    if current_lesson:
        submitted_assignment_ids = list(Submission.objects.filter(
            student=request.user, assignment__lesson=current_lesson
        ).values_list('assignment_id', flat=True))

    context = {
        'course': course,
        'enrollment': enrollment,
        'lessons': lessons,
        'current_lesson': current_lesson,
        'completed_lessons': list(completed_lessons),
        'accessible_lessons': accessible_lessons,
        'current_lesson_gate': current_lesson_gate,
        'submitted_assignment_ids': submitted_assignment_ids,
        'quiz_required_pass_score': QUIZ_REQUIRED_PASS_SCORE,
        'quiz_required_attempts': QUIZ_REQUIRED_MAX_ATTEMPTS,
        'quiz_required_question_count': QUIZ_REQUIRED_QUESTION_COUNT,
    }
    return render(request, 'courses/course_learn.html', context)


@login_required
def mark_lesson_complete(request, course_slug, lesson_id):
    """Darsni tugatilgan deb belgilash"""
    if not _require_student(request):
        return redirect('dashboard')

    lesson = get_object_or_404(Lesson, id=lesson_id, course__slug=course_slug)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)
    gate_status = _get_lesson_gate_status(request.user, lesson)

    if not gate_status['can_complete']:
        messages.error(request, "Darsni tugatishdan oldin talablar bajarilishi kerak.")
        for reason in gate_status['reasons']:
            messages.warning(request, reason)
        return redirect(f"{request.path.rsplit('/', 4)[0]}/learn/?lesson={lesson.id}")

    progress, created = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)

    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(lesson.xp_reward, f"'{lesson.title}' darsini tugatish")

        total_lessons = lesson.course.lessons.filter(is_published=True).count()
        completed_lessons = LessonProgress.objects.filter(
            student=request.user, lesson__course=lesson.course, completed=True
        ).count()

        enrollment.progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

        if enrollment.progress >= 100:
            enrollment.completed = True
            enrollment.completed_at = timezone.now()
            Certificate.objects.get_or_create(student=request.user, course=lesson.course)
            messages.success(request, f"Tabriklaymiz! '{lesson.course.title}' kursini tugatdingiz!")

        enrollment.save()

    next_lesson = lesson.course.lessons.filter(is_published=True, order__gt=lesson.order).order_by('order').first()

    if next_lesson:
        return redirect(f"{request.path.rsplit('/', 4)[0]}/learn/?lesson={next_lesson.id}")

    return redirect('course_learn', slug=lesson.course.slug)


# ==========================================
# QUIZ
# ==========================================
@login_required
def quiz_detail(request, pk):
    if not _require_student(request):
        return redirect('dashboard')

    quiz = get_object_or_404(Quiz, pk=pk)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=quiz.lesson.course)

    attempts = QuizAttempt.objects.filter(student=request.user, quiz=quiz).order_by('-started_at')
    best_score = attempts.order_by('-score').first()
    has_passed_required = attempts.filter(score__gte=QUIZ_REQUIRED_PASS_SCORE).exists()
    questions = quiz.questions.all()
    can_attempt = (
        (not has_passed_required)
        and attempts.count() < QUIZ_REQUIRED_MAX_ATTEMPTS
        and questions.count() >= QUIZ_REQUIRED_QUESTION_COUNT
    )

    context = {
        'quiz': quiz,
        'questions': questions,
        'attempts': attempts,
        'user_attempts': attempts,
        'best_score': best_score,
        'can_attempt': can_attempt,
        'required_pass_score': QUIZ_REQUIRED_PASS_SCORE,
        'required_attempts': QUIZ_REQUIRED_MAX_ATTEMPTS,
        'required_question_count': QUIZ_REQUIRED_QUESTION_COUNT,
        'question_count_ok': questions.count() >= QUIZ_REQUIRED_QUESTION_COUNT,
        'attempts_used': attempts.count(),
        'is_teacher': False,
    }
    return render(request, 'courses/quiz_detail.html', context)


@login_required
def quiz_take(request, pk):
    if not _require_student(request):
        return redirect('dashboard')

    quiz = get_object_or_404(Quiz, pk=pk)
    get_object_or_404(Enrollment, student=request.user, course=quiz.lesson.course)

    attempts_qs = QuizAttempt.objects.filter(student=request.user, quiz=quiz)
    if attempts_qs.filter(score__gte=QUIZ_REQUIRED_PASS_SCORE).exists():
        messages.success(request, "Siz bu testdan allaqachon o'tgansiz.")
        return redirect('quiz_detail', pk=pk)

    attempts_count = attempts_qs.count()
    if attempts_count >= QUIZ_REQUIRED_MAX_ATTEMPTS:
        messages.error(request, "Maksimal urinish soniga yetdingiz!")
        return redirect('quiz_detail', pk=pk)

    questions = quiz.questions.all()
    if questions.count() < QUIZ_REQUIRED_QUESTION_COUNT:
        messages.error(
            request,
            f"Bu testda kamida {QUIZ_REQUIRED_QUESTION_COUNT} ta savol bo'lishi kerak."
        )
        return redirect('quiz_detail', pk=pk)

    if quiz.shuffle_questions:
        questions = questions.order_by('?')

    if request.method == 'POST':
        attempt = QuizAttempt.objects.create(student=request.user, quiz=quiz)

        correct = 0
        total_points = 0
        earned_points = 0

        for question in questions:
            total_points += question.points
            selected_ids = request.POST.getlist(f'question_{question.id}')

            QuizResponse.objects.create(
                attempt=attempt,
                question=question,
                selected_answers=','.join(selected_ids)
            )

            correct_ids = set(str(a.id) for a in question.answers.filter(is_correct=True))
            if correct_ids == set(selected_ids):
                correct += 1
                earned_points += question.points

        score = int((earned_points / total_points) * 100) if total_points > 0 else 0
        passed = score >= QUIZ_REQUIRED_PASS_SCORE

        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.correct_answers = correct
        attempt.wrong_answers = len(questions) - correct

        if passed:
            attempt.xp_earned = quiz.xp_reward
            xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
            xp_profile.add_xp(quiz.xp_reward, f"'{quiz.title}' testini topshirish")
        else:
            attempts_used = QuizAttempt.objects.filter(student=request.user, quiz=quiz).count()
            if attempts_used >= QUIZ_REQUIRED_MAX_ATTEMPTS:
                _apply_quiz_failure_penalty(request.user, quiz)

        attempt.save()
        return redirect('quiz_result', pk=attempt.pk)

    return render(request, 'courses/quiz_take.html', {'quiz': quiz, 'questions': questions})


@login_required
def quiz_result(request, pk):
    if not _require_student(request):
        return redirect('dashboard')

    attempt = get_object_or_404(QuizAttempt, pk=pk, student=request.user)
    responses = attempt.responses.select_related('question')
    return render(request, 'courses/quiz_result.html', {'attempt': attempt, 'responses': responses})


@login_required
def quiz_statistics(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    if quiz.lesson.course.teacher != request.user:
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('dashboard')

    attempts = QuizAttempt.objects.filter(quiz=quiz)
    total_attempts = attempts.count()
    passed_attempts = attempts.filter(passed=True).count()
    avg_score = attempts.aggregate(avg=Avg('score'))['avg'] or 0
    pass_rate = (passed_attempts / total_attempts * 100) if total_attempts > 0 else 0

    context = {
        'quiz': quiz,
        'total_attempts': total_attempts,
        'passed_attempts': passed_attempts,
        'avg_score': avg_score,
        'pass_rate': pass_rate,
        'attempts': attempts.order_by('-started_at')[:20],
    }
    return render(request, 'courses/quiz_statistics.html', context)


# ==========================================
# ASSIGNMENT
# ==========================================
@login_required
def assignment_detail(request, pk):
    if not _require_student(request):
        return redirect('dashboard')

    assignment = get_object_or_404(Assignment, pk=pk)
    submission = Submission.objects.filter(student=request.user, assignment=assignment).first()
    ai_recommendation = None
    if submission:
        ai_recommendation = AIGradeRecommendation.objects.filter(submission=submission).first()
    return render(request, 'courses/assignment_detail.html', {
        'assignment': assignment,
        'submission': submission,
        'ai_recommendation': ai_recommendation
    })


@login_required
def assignment_submit(request, pk):
    if not _require_student(request):
        return redirect('dashboard')

    assignment = get_object_or_404(Assignment, pk=pk)

    existing = Submission.objects.filter(student=request.user, assignment=assignment).first()
    if existing:
        messages.info(request, "Siz allaqachon topshiriq yuborgansiz!")
        return redirect('assignment_detail', pk=pk)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.student = request.user
            submission.assignment = assignment
            submission.save()

            ai_analysis = analyze_submission_with_ai(submission, assignment)
            if ai_analysis:
                AIGradeRecommendation.objects.update_or_create(
                    submission=submission,
                    defaults={
                        'ai_score': ai_analysis['score'],
                        'max_score': assignment.max_score or 100,
                        'confidence': ai_analysis['confidence'],
                        'analysis': ai_analysis['analysis'],
                        'strengths': ai_analysis['strengths'],
                        'weaknesses': ai_analysis['weaknesses'],
                        'suggestions': ai_analysis['suggestions']
                    }
                )
                messages.success(
                    request,
                    f"Topshiriq yuborildi. AI tavsiya bahosi: {ai_analysis['score']}/{assignment.max_score}."
                )
            else:
                messages.success(request, "Topshiriq yuborildi!")
            return redirect('assignment_detail', pk=pk)
    else:
        form = SubmissionForm()

    return render(request, 'courses/assignment_submit.html', {'form': form, 'assignment': assignment})


# ==========================================
# CERTIFICATE
# ==========================================
@login_required
def my_certificates(request):
    certificates = Certificate.objects.filter(student=request.user).select_related('course')
    return render(request, 'courses/my_certificates.html', {'certificates': certificates})


@login_required
def certificate_detail(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk, student=request.user)
    theme = request.GET.get('theme', 'classic')
    return render(request, 'courses/certificate_detail.html', {
        'certificate': certificate,
        'theme': theme if theme in {'classic', 'royal', 'modern'} else 'classic',
    })


@login_required
def certificate_download(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk, student=request.user)
    theme = request.GET.get('theme', 'classic')
    pdf_buffer = CertificateGenerator(certificate, theme=theme).generate()
    safe_theme = theme if theme in {'classic', 'royal', 'modern'} else 'classic'
    filename = f"certificate-{certificate.certificate_number}-{safe_theme}.pdf"
    return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


def certificate_verify(request, certificate_number):
    certificate = get_object_or_404(Certificate, certificate_number=certificate_number)
    return render(request, 'courses/certificate_verify.html', {'certificate': certificate})


# ==========================================
# REVIEW
# ==========================================
@login_required
def review_create(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if not Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.error(request, "Sharh qoldirish uchun kursga yozilishingiz kerak!")
        return redirect('course_detail', slug=slug)

    if CourseReview.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "Siz allaqachon sharh qoldirgansiz!")
        return redirect('course_detail', slug=slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.course = course
            review.save()

            avg_rating = course.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            course.average_rating = avg_rating
            course.total_reviews = course.reviews.count()
            course.save()

            messages.success(request, "Sharh qo'shildi!")
            return redirect('course_detail', slug=slug)
    else:
        form = ReviewForm()

    return render(request, 'courses/reviews/review_form.html', {'form': form, 'course': course})


@login_required
def review_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    reviews = course.reviews.filter(is_approved=True).order_by('-created_at')
    paginator = Paginator(reviews, 10)
    reviews = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/reviews/review_list.html', {'course': course, 'reviews': reviews})


# ==========================================
# DISCUSSION
# ==========================================
@login_required
def discussion_list(request, slug):
    course = get_object_or_404(Course, slug=slug)
    discussions = course.discussions.order_by('-is_pinned', '-created_at')
    return render(request, 'courses/discussion_list.html', {'course': course, 'discussions': discussions})


@login_required
def discussion_create(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.course = course
            discussion.author = request.user
            discussion.save()
            messages.success(request, "Muhokama yaratildi!")
            return redirect('discussion_list', slug=slug)
    else:
        form = DiscussionForm()

    return render(request, 'courses/discussion_form.html', {'form': form, 'course': course})


@login_required
def discussion_detail(request, pk):
    discussion = get_object_or_404(Discussion, pk=pk)
    discussion.views_count += 1
    discussion.save()

    replies = discussion.replies.order_by('created_at')

    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.discussion = discussion
            reply.author = request.user
            reply.save()
            messages.success(request, "Javob qo'shildi!")
            return redirect('discussion_detail', pk=pk)
    else:
        form = ReplyForm()

    return render(request, 'courses/discussion_detail.html',
                  {'discussion': discussion, 'replies': replies, 'form': form})


@login_required
def reply_delete(request, pk):
    reply = get_object_or_404(Reply, pk=pk, author=request.user)
    discussion_pk = reply.discussion.pk
    if request.method == 'POST':
        reply.delete()
        messages.success(request, "Javob o'chirildi!")
    return redirect('discussion_detail', pk=discussion_pk)


# ==========================================
# NOTIFICATION
# ==========================================
@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
        return redirect('notification_list')

    paginator = Paginator(notifications, 20)
    notifications = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/notification_list.html', {'notifications': notifications})


@login_required
def notification_recent(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]

    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message[:50],
        'type': n.notification_type,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
    } for n in notifications]

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'notifications': data, 'unread_count': unread_count})


# ==========================================
# PAYMENT
# ==========================================
@login_required
def payment_checkout(request, slug):
    course = get_object_or_404(Course, slug=slug)

    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return redirect('course_learn', slug=slug)

    final_price = course.discount_price if course.discount_price else course.price
    discount = 0
    promo_code = None

    if request.method == 'POST':
        code = request.POST.get('promo_code', '').strip().upper()
        if code:
            try:
                promo = PromoCode.objects.get(
                    code=code, is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now()
                )
                if promo.current_uses < promo.max_uses:
                    if promo.discount_type == 'percent':
                        discount = final_price * (promo.discount_value / 100)
                    else:
                        discount = promo.discount_value
                    final_price = max(0, final_price - discount)
                    promo_code = promo
                    messages.success(request, f"Promo kod qo'llanildi!")
            except PromoCode.DoesNotExist:
                messages.error(request, "Noto'g'ri promo kod!")

    return render(request, 'courses/payment_checkout.html', {
        'course': course, 'final_price': final_price, 'discount': discount, 'promo_code': promo_code
    })


@login_required
def payment_process(request, slug):
    if request.method != 'POST':
        return redirect('payment_checkout', slug=slug)

    course = get_object_or_404(Course, slug=slug)
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method', 'payme')

    Payment.objects.create(
        student=request.user, course=course, amount=amount,
        payment_method=payment_method, status='completed',
        transaction_id=f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    )

    Enrollment.objects.create(student=request.user, course=course)
    course.total_students += 1
    course.save()

    return redirect('payment_success', slug=slug)


@login_required
def payment_success(request, slug):
    course = get_object_or_404(Course, slug=slug)
    return render(request, 'courses/payment_success.html', {'course': course})


# ==========================================
# WISHLIST
# ==========================================
@login_required
def wishlist_view(request):
    wishlist = Wishlist.objects.filter(user=request.user).select_related('course')
    return render(request, 'courses/wishlist.html', {'wishlist': wishlist})


@login_required
def wishlist_toggle(request, slug):
    course = get_object_or_404(Course, slug=slug)
    wishlist_item = Wishlist.objects.filter(user=request.user, course=course)

    if wishlist_item.exists():
        wishlist_item.delete()
        messages.info(request, "Kurs istaklar ro'yxatidan o'chirildi")
    else:
        Wishlist.objects.create(user=request.user, course=course)
        messages.success(request, "Kurs istaklar ro'yxatiga qo'shildi")

    return redirect(request.META.get('HTTP_REFERER', 'course_list'))


# ==========================================
# TEACHER PANEL
# ==========================================
@login_required
def teacher_dashboard(request):
    if not _require_teacher(request):
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user)
    total_students = Enrollment.objects.filter(course__teacher=request.user).count()
    total_revenue = Payment.objects.filter(
        course__teacher=request.user, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    recent_enrollments = Enrollment.objects.filter(
        course__teacher=request.user
    ).select_related('student', 'course').order_by('-enrolled_at')[:10]

    # Baholanmagan topshiriqlar
    pending_submissions = Submission.objects.filter(
        assignment__lesson__course__teacher=request.user,
        is_graded=False
    ).select_related('student', 'assignment', 'assignment__lesson__course').order_by('-submitted_at')[:10]
    pending_count = Submission.objects.filter(
        assignment__lesson__course__teacher=request.user,
        is_graded=False
    ).count()

    context = {
        'courses': courses,
        'total_students': total_students,
        'total_courses': courses.count(),
        'total_revenue': total_revenue,
        'recent_enrollments': recent_enrollments,
        'pending_submissions': pending_submissions,
        'pending_count': pending_count,
    }
    return render(request, 'courses/teacher/dashboard.html', context)


@login_required
def teacher_courses(request):
    if not _require_teacher(request):
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user).order_by('-created_at')
    for course in courses:
        course.enrolled_count = Enrollment.objects.filter(course=course).count()

    return render(request, 'courses/teacher/courses.html', {'courses': courses})


@login_required
def teacher_course_create(request):
    if not _require_teacher(request):
        return redirect('dashboard')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            messages.success(request, "Kurs muvaffaqiyatli yaratildi!")
            return redirect('teacher_course_edit', slug=course.slug)
        messages.error(request, "Forma xatolari bor. Majburiy maydonlarni to'ldiring.")
    else:
        form = CourseForm()

    return render(request, 'courses/teacher/course_create.html', {'form': form})


@login_required
def teacher_course_edit(request, slug):
    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Kurs yangilandi!")
            return redirect('teacher_courses')
        messages.error(request, "Kurs saqlanmadi. Forma xatolarini tekshiring.")
    else:
        form = CourseForm(instance=course)

    lessons = course.lessons.all().order_by('order')
    return render(request, 'courses/teacher/course_edit.html', {'form': form, 'course': course, 'lessons': lessons})


@login_required
def teacher_course_students(request, slug):
    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student').order_by('-enrolled_at')

    status = request.GET.get('status')
    if status == 'completed':
        enrollments = enrollments.filter(completed=True)
    elif status == 'in_progress':
        enrollments = enrollments.filter(completed=False)

    context = {
        'course': course,
        'enrollments': enrollments,
        'current_status': status,
        'total_count': Enrollment.objects.filter(course=course).count(),
        'completed_count': Enrollment.objects.filter(course=course, completed=True).count(),
    }
    return render(request, 'courses/teacher/course_students.html', context)


@login_required
def teacher_student_detail(request, course_slug, user_id):
    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=course_slug, teacher=request.user)
    enrollment = get_object_or_404(Enrollment, course=course, student_id=user_id)

    lessons = course.lessons.all().order_by('order')
    lesson_statuses = []

    for lesson in lessons:
        try:
            progress = LessonProgress.objects.get(
                student=enrollment.student,
                lesson=lesson
            )
            lesson_statuses.append({
                'lesson': lesson,
                'completed': progress.completed,
                'completed_at': progress.updated_at if progress.completed else None,
            })
        except LessonProgress.DoesNotExist:
            lesson_statuses.append({
                'lesson': lesson,
                'completed': False,
                'completed_at': None,
            })

    total_lessons = lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        student=enrollment.student,
        lesson__course=course,
        completed=True
    ).count()

    progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    context = {
        'course': course,
        'enrollment': enrollment,
        'lesson_statuses': lesson_statuses,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'progress_percent': progress_percent,
    }
    return render(request, 'accounts/teacher_student_detail.html', context)


@login_required
def teacher_course_delete(request, slug):
    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == 'POST':
        course.delete()
        messages.success(request, "Kurs o'chirildi!")
        return redirect('teacher_courses')

    return render(request, 'courses/teacher/course_delete.html', {'course': course})


@login_required
def teacher_lesson_create(request, course_slug):
    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=course_slug, teacher=request.user)

    last_order = course.lessons.order_by('-order').first()
    next_order = (last_order.order + 1) if last_order else 1
    assignment_form = AssignmentForm(prefix='assignment')
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        assignment_form = AssignmentForm(request.POST, request.FILES, prefix='assignment')

        assignment_requested = (
            bool((request.POST.get('assignment-title') or '').strip())
            or bool((request.POST.get('assignment-description') or '').strip())
            or bool(request.FILES.get('assignment-attachment'))
        )

        if form.is_valid():
            if assignment_requested and not assignment_form.is_valid():
                messages.error(request, "Topshiriq bo'limida xatolar bor. Iltimos tekshiring.")
                return render(request, 'courses/teacher/lesson_form.html', {
                    'form': form,
                    'assignment_form': assignment_form,
                    'course': course,
                    'action': 'create'
                })

            lesson = form.save(commit=False)
            lesson.course = course
            if not lesson.order:
                lesson.order = next_order
            lesson.save()

            if assignment_requested:
                assignment = assignment_form.save(commit=False)
                assignment.lesson = lesson
                assignment.save()

            messages.success(request, "Dars qo'shildi!")
            return redirect('teacher_course_edit', slug=course.slug)
    else:
        form = LessonForm(initial={'order': next_order, 'is_published': True})
        assignment_form = AssignmentForm(prefix='assignment')

    return render(request, 'courses/teacher/lesson_form.html', {
        'form': form,
        'assignment_form': assignment_form,
        'course': course,
        'action': 'create'
    })


@login_required
def teacher_lesson_edit(request, pk):
    if not _require_teacher(request):
        return redirect('dashboard')

    lesson = get_object_or_404(Lesson, pk=pk, course__teacher=request.user)
    existing_assignment = lesson.assignments.order_by('created_at').first()

    assignment_form = AssignmentForm(prefix='assignment', instance=existing_assignment)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        assignment_form = AssignmentForm(
            request.POST,
            request.FILES,
            prefix='assignment',
            instance=existing_assignment
        )

        assignment_requested = (
            bool((request.POST.get('assignment-title') or '').strip())
            or bool((request.POST.get('assignment-description') or '').strip())
            or bool(request.FILES.get('assignment-attachment'))
            or existing_assignment is not None
        )

        if form.is_valid():
            if assignment_requested and not assignment_form.is_valid():
                messages.error(request, "Topshiriq bo'limida xatolar bor. Iltimos tekshiring.")
                return render(request, 'courses/teacher/lesson_form.html', {
                    'form': form,
                    'assignment_form': assignment_form,
                    'lesson': lesson,
                    'course': lesson.course,
                    'action': 'edit'
                })

            form.save()

            if assignment_requested and assignment_form.is_valid():
                assignment = assignment_form.save(commit=False)
                assignment.lesson = lesson
                assignment.save()

            messages.success(request, "Dars yangilandi!")
            return redirect('teacher_course_edit', slug=lesson.course.slug)
    else:
        form = LessonForm(instance=lesson)
        assignment_form = AssignmentForm(prefix='assignment', instance=existing_assignment)

    return render(request, 'courses/teacher/lesson_form.html',
                  {
                      'form': form,
                      'assignment_form': assignment_form,
                      'lesson': lesson,
                      'course': lesson.course,
                      'action': 'edit'
                  })


@login_required
def teacher_lesson_delete(request, pk):
    if not _require_teacher(request):
        return redirect('dashboard')

    lesson = get_object_or_404(Lesson, pk=pk, course__teacher=request.user)
    course_slug = lesson.course.slug

    if request.method == 'POST':
        lesson.delete()
        messages.success(request, "Dars o'chirildi!")
        return redirect('teacher_course_edit', slug=course_slug)

    return render(request, 'courses/teacher/lesson_delete.html', {'lesson': lesson})


@login_required
def teacher_statistics(request):
    if not _require_teacher(request):
        return redirect('dashboard')

    courses = Course.objects.filter(teacher=request.user)
    total_students = Enrollment.objects.filter(course__teacher=request.user).count()
    completed_students = Enrollment.objects.filter(course__teacher=request.user, completed=True).count()
    total_revenue = Payment.objects.filter(
        course__teacher=request.user, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'courses': courses,
        'total_courses': courses.count(),
        'total_students': total_students,
        'completed_students': completed_students,
        'total_revenue': total_revenue,
    }
    return render(request, 'courses/teacher/statistics.html', context)


# ==========================================
# GAMIFICATION
# ==========================================
@login_required
def gamification_profile(request):
    xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
    user_badges = UserBadge.objects.filter(user=request.user).select_related('badge')
    transactions = XPTransaction.objects.filter(user=request.user).order_by('-created_at')[:20]

    return render(request, 'courses/gamification/profile.html', {
        'xp_profile': xp_profile, 'user_badges': user_badges, 'transactions': transactions
    })


@login_required
def leaderboard(request):
    top_users = UserXP.objects.select_related('user').order_by('-total_xp')[:50]
    user_xp, _ = UserXP.objects.get_or_create(user=request.user)
    user_rank = UserXP.objects.filter(total_xp__gt=user_xp.total_xp).count() + 1

    return render(request, 'courses/gamification/leaderboard.html', {
        'top_users': top_users, 'user_rank': user_rank, 'user_xp': user_xp
    })


@login_required
def daily_challenges(request):
    today = timezone.now().date()
    challenges = DailyChallenge.objects.filter(date=today, is_active=True)
    completed_ids = UserChallenge.objects.filter(
        user=request.user, challenge__date=today
    ).values_list('challenge_id', flat=True)

    return render(request, 'courses/gamification/daily_challenges.html', {
        'challenges': challenges, 'completed_ids': list(completed_ids)
    })


# ==========================================
# CHATBOT
# ==========================================
def generate_ai_response(message, course=None):
    system_prompt = """Sen LMS platformasining AI yordamchisisisan. O'zbek tilida javob ber.
Dasturlash, Django, Python va boshqa mavzularda yordam ber. Qisqa va foydali javoblar ber."""

    if course:
        system_prompt += f"\n\nHozir foydalanuvchi '{course.title}' kursi bilan ishlayapti."

    result = _call_gemini(
        [{"text": f"{system_prompt}\n\nSavol: {message}"}],
        timeout=30,
    )
    if result['ok']:
        return result['text']

    return _fallback_chat_response(message, course=course, error_type=result.get('error_type'))


@login_required
def chatbot_view(request, slug=None):
    if not _require_ai_mentor_access(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug) if slug else None

    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()

            if not message:
                return JsonResponse({'error': 'Xabar bo\'sh'}, status=400)

            ai_response = generate_ai_response(message, course)

            return JsonResponse({
                'response': ai_response,
                'created_at': timezone.now().strftime('%H:%M')
            })
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)

    return render(request, 'courses/chatbot/chat.html', {'course': course})


@login_required
def chatbot_send(request):
    if not _require_ai_mentor_access(request):
        return JsonResponse({'error': "Ruxsat yo'q"}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST kerak'}, status=405)

    message = request.POST.get('message', '').strip()
    course_slug = request.POST.get('course_slug')

    if not message:
        return JsonResponse({'error': 'Xabar bo\'sh'}, status=400)

    course = get_object_or_404(Course, slug=course_slug) if course_slug else None
    ai_response = generate_ai_response(message, course)

    return JsonResponse({
        'success': True,
        'message': message,
        'response': ai_response,
        'created_at': timezone.now().strftime('%H:%M')
    })


@login_required
def chatbot_history(request):
    if not _require_ai_mentor_access(request):
        return redirect('dashboard')

    return render(request, 'courses/chatbot/history.html', {'messages': []})


@login_required
def chatbot_clear(request):
    if not _require_ai_mentor_access(request):
        return redirect('dashboard')

    messages.success(request, "AI Mentor sessiyasi tozalandi.")
    return redirect('chatbot_view')


# ==========================================
# CODE EDITOR
# ==========================================
@login_required
def code_editor(request):
    return render(request, 'courses/code_editor/editor.html')


@login_required
def code_execute(request):
    """Python kodini nisbatan xavfsiz muhitda ishga tushirish"""
    import ast
    import contextlib
    import io

    if request.method != 'POST':
        return JsonResponse({'error': 'POST kerak'}, status=405)

    try:
        import json
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', 'python')

        if not code.strip():
            return JsonResponse({'error': 'Kod bo\'sh'}, status=400)

        if language == 'python':
            tree = ast.parse(code, mode='exec')
            blocked_nodes = (
                ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Try, ast.Raise,
                ast.ClassDef, ast.Lambda, ast.Global, ast.Nonlocal
            )
            for node in ast.walk(tree):
                if isinstance(node, blocked_nodes):
                    return JsonResponse({'success': False, 'error': "Xavfsizlik: bu operator taqiqlangan"})
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in {'eval', 'exec', 'open', 'input', '__import__'}:
                        return JsonResponse({'success': False, 'error': "Xavfsizlik: xavfli funksiya taqiqlangan"})
                if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
                    return JsonResponse({'success': False, 'error': "Xavfsizlik: maxsus atributlar taqiqlangan"})

            safe_builtins = {
                'print': print,
                'len': len,
                'range': range,
                'min': min,
                'max': max,
                'sum': sum,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'enumerate': enumerate,
                'zip': zip,
            }

            local_scope = {}
            output_stream = io.StringIO()
            with contextlib.redirect_stdout(output_stream):
                exec(compile(tree, '<student_code>', 'exec'), {'__builtins__': safe_builtins}, local_scope)

            output = output_stream.getvalue().strip()
            if not output:
                output = "Dastur muvaffaqiyatli ishga tushdi (natija yo'q)"
            return JsonResponse({'success': True, 'output': output})

        return JsonResponse({'error': 'Noma\'lum til'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Noto\'g\'ri JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ==========================================
# STUDENT STATISTICS
# ==========================================
@login_required
def student_statistics(request):
    if not _require_student(request):
        return redirect('dashboard')

    enrollments = Enrollment.objects.filter(student=request.user)
    return render(request, 'courses/student_statistics.html', {
        'total_enrolled': enrollments.count(),
        'completed': enrollments.filter(completed=True).count(),
        'in_progress': enrollments.filter(completed=False).count(),
    })


# ==========================================
# AI GRADING ASSISTANT
# ==========================================

def analyze_submission_with_ai(submission, assignment):
    """Topshiriqni AI bilan tahlil qilish va baho tavsiya etish."""
    import json as _json
    import re as _re

    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    max_score = assignment.max_score or 100

    if not api_key:
        return _build_fallback_ai_grade(submission, assignment, "GEMINI_API_KEY topilmadi")

    # Topshiriq matni (description + instructions)
    assignment_text = assignment.description or ''
    if assignment.instructions:
        assignment_text += f"\n\nKo'rsatmalar:\n{assignment.instructions}"

    teacher_file_data = _extract_file_for_ai(assignment.attachment, "O'qituvchi vazifa")

    # Talaba matn javobi
    submission_text = submission.content or ''
    student_file_data = _extract_file_for_ai(submission.file, "Talaba javobi")

    assignment_text += teacher_file_data['text']
    submission_text += student_file_data['text']
    extra_parts = teacher_file_data['parts'] + student_file_data['parts']
    file_notes = teacher_file_data['notes'] + student_file_data['notes']

    if not submission_text and not extra_parts:
        submission_text = "Matn javobi yo'q"

    try:
        prompt = f"""Sen professional ta'lim o'qituvchisisisan. Vazifa talablari bilan talaba javobini taqqoslab, moslik va sifat bo'yicha baho tavsiya et.

TOPSHIRIQ:
{assignment_text}

Maksimal ball: {max_score}

TALABA JAVOBI:
{submission_text}

QO'SHIMCHA ESLATMA:
{chr(10).join(file_notes) if file_notes else "Qo'shimcha eslatma yo'q"}

BAHOLASH QOIDASI:
- O'qituvchi bergan vazifa matni va ilova faylini asosiy mezon deb ol.
- Talaba matni va ilova faylini shu mezonlarga nisbatan solishtir.
- Javobning mavzuga mosligi, to'liqligi, aniqligi va fayldagi dalillarini tekshir.
- Agar talaba noto'g'ri format yoki mavzudan chetga chiqqan bo'lsa ballni pasaytir.
- Ball 0 dan {max_score} gacha bo'lsin va aynan maksimal ball mezoniga nisbatan hisobla.

Quyidagi formatda javob ber (JSON):
{{
    "score": (tavsiya etilgan ball 0-{max_score}),
    "confidence": (ishonch darajasi 0.0-1.0),
    "analysis": "O'qituvchi vazifasi bilan solishtirilgan umumiy tahlil va nechchi ballga mosligi",
    "strengths": "Kuchli tomonlar (bullet points)",
    "weaknesses": "Zaif tomonlar (bullet points)",
    "suggestions": "Yaxshilash takliflari"
}}

MUHIM: Faqat JSON formatda javob ber, boshqa matn qo'shma!"""

        parts = [{"text": prompt}] + extra_parts

        result = _call_gemini(parts, timeout=45)
        if not result['ok']:
            print(f"Gemini API xatosi: {result.get('error_type')} - {result.get('message')}")
            return _build_fallback_ai_grade(submission, assignment, result.get('message', 'AI mavjud emas'))

        response_text = result['text'].strip()

        # JSON'ni topish
        json_match = _re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            response_text = json_match.group()
        response_text = response_text.replace('```json', '').replace('```', '').strip()

        ai_data = _json.loads(response_text)

        return {
            'score': _clamp_int(
                ai_data.get('score', max_score * 0.7),
                int(max_score * 0.7),
                minimum=0,
                maximum=max_score,
            ),
            'confidence': _clamp_float(
                ai_data.get('confidence', 0.7),
                0.7,
                minimum=0.0,
                maximum=1.0,
            ),
            'analysis': ai_data.get('analysis', 'Tahlil mavjud emas'),
            'strengths': ai_data.get('strengths', ''),
            'weaknesses': ai_data.get('weaknesses', ''),
            'suggestions': ai_data.get('suggestions', '')
        }

    except Exception as e:
        print(f"AI tahlil xatosi: {e}")
        return _build_fallback_ai_grade(submission, assignment, str(e))


@login_required
def teacher_grade_submission(request, pk):
    """O'qituvchi topshiriqni baholaydi (AI tavsiyasi bilan)"""
    from .models import AIGradeRecommendation

    if not _require_teacher(request):
        return redirect('dashboard')

    submission = get_object_or_404(Submission, pk=pk)
    assignment = submission.assignment

    # Faqat o'qituvchi baholashi mumkin
    if assignment.lesson.course.teacher != request.user:
        messages.error(request, "Sizda ruxsat yo'q!")
        return redirect('dashboard')

    # AI tavsiyasini olish yoki yangidan tahlil qilish
    ai_recommendation = None
    reanalyze = request.GET.get('reanalyze') == '1'
    try:
        ai_recommendation = AIGradeRecommendation.objects.get(submission=submission)
        # Agar avvalgi tahlil xatolik bilan saqlangan bo'lsa yoki qayta tahlil so'ralsa
        if reanalyze or 'xatolik' in (ai_recommendation.analysis or '').lower() or ai_recommendation.analysis == 'Tahlil mavjud emas':
            ai_analysis = analyze_submission_with_ai(submission, assignment)
            if ai_analysis:
                ai_recommendation.ai_score = ai_analysis['score']
                ai_recommendation.max_score = assignment.max_score or 100
                ai_recommendation.confidence = ai_analysis['confidence']
                ai_recommendation.analysis = ai_analysis['analysis']
                ai_recommendation.strengths = ai_analysis['strengths']
                ai_recommendation.weaknesses = ai_analysis['weaknesses']
                ai_recommendation.suggestions = ai_analysis['suggestions']
                ai_recommendation.save()
    except AIGradeRecommendation.DoesNotExist:
        # Yangi AI tahlil qilish
        ai_analysis = analyze_submission_with_ai(submission, assignment)
        if ai_analysis:
            ai_recommendation = AIGradeRecommendation.objects.create(
                submission=submission,
                ai_score=ai_analysis['score'],
                max_score=assignment.max_score or 100,
                confidence=ai_analysis['confidence'],
                analysis=ai_analysis['analysis'],
                strengths=ai_analysis['strengths'],
                weaknesses=ai_analysis['weaknesses'],
                suggestions=ai_analysis['suggestions']
            )

    if request.method == 'POST':
        raw_score = request.POST.get('score', '')
        teacher_score = _parse_bounded_score(raw_score, assignment.max_score or 100)
        teacher_feedback = request.POST.get('feedback', '').strip()

        if teacher_score is None or str(raw_score).strip() == '':
            messages.error(request, "Ball son ko'rinishida kiritilishi kerak.")
            context = {
                'submission': submission,
                'assignment': assignment,
                'ai_recommendation': ai_recommendation,
            }
            return render(request, 'courses/teacher/grade_submission.html', context, status=400)

        # Submission'ni yangilash
        submission.score = teacher_score
        submission.feedback = teacher_feedback
        submission.graded_by = request.user
        submission.is_graded = True
        submission.graded_at = timezone.now()
        submission.save()

        # AI recommendation'ni yangilash
        if ai_recommendation:
            ai_recommendation.teacher_score = teacher_score
            ai_recommendation.teacher_feedback = teacher_feedback
            ai_recommendation.is_reviewed = True
            ai_recommendation.reviewed_at = timezone.now()
            ai_recommendation.calculate_difference()
            ai_recommendation.save()

        # Talabaga bildirishnoma yuborish
        Notification.objects.create(
            recipient=submission.student,
            title="Topshiriqingiz baholandi!",
            message=f'"{assignment.title}" topshirig\'ingiz baholandi. '
                    f'Ball: {teacher_score}/{assignment.max_score}.',
            notification_type='grade',
            link=f'/assignment/{assignment.pk}/',
        )

        messages.success(request, f"Topshiriq baholandi! Ball: {teacher_score}/{assignment.max_score}")
        return redirect('teacher_submissions', slug=assignment.lesson.course.slug)

    context = {
        'submission': submission,
        'assignment': assignment,
        'ai_recommendation': ai_recommendation,
    }
    return render(request, 'courses/teacher/grade_submission.html', context)


@login_required
def teacher_submissions(request, slug):
    """O'qituvchining barcha topshiriqlar ro'yxati"""
    from .models import AIGradeRecommendation

    if not _require_teacher(request):
        return redirect('dashboard')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    submissions = Submission.objects.filter(
        assignment__lesson__course=course
    ).select_related('student', 'assignment', 'assignment__lesson').order_by('-submitted_at')

    # Filter
    status = request.GET.get('status')
    if status == 'pending':
        submissions = submissions.filter(is_graded=False)
    elif status == 'graded':
        submissions = submissions.filter(is_graded=True)

    submission_list = list(submissions)
    ai_recommendations = AIGradeRecommendation.objects.filter(
        submission__in=submission_list
    ).in_bulk(field_name='submission_id')

    for submission in submission_list:
        submission.ai_rec = ai_recommendations.get(submission.id)

    context = {
        'course': course,
        'submissions': submission_list,
        'current_status': status,
    }
    return render(request, 'courses/teacher/submissions.html', context)


@login_required
def supervisor_dashboard(request):
    """Nazoratchi paneli - AI va o'qituvchi baholashlarini taqqoslash"""
    from .models import AIGradeRecommendation

    if not _require_supervisor(request):
        return redirect('dashboard')

    # Barcha AI recommendations
    recommendations = AIGradeRecommendation.objects.filter(
        is_reviewed=True
    ).select_related(
        'submission',
        'submission__student',
        'submission__assignment',
        'submission__assignment__lesson__course__teacher'
    ).order_by('-reviewed_at')

    # Statistika
    total_graded = recommendations.count()
    avg_ai_score = recommendations.aggregate(avg=Avg('ai_score'))['avg'] or 0
    avg_teacher_score = recommendations.aggregate(avg=Avg('teacher_score'))['avg'] or 0
    avg_difference = recommendations.aggregate(avg=Avg('score_difference'))['avg'] or 0

    # Katta farq bo'lgan topshiriqlar
    large_differences = recommendations.filter(score_difference__gte=20).order_by('-score_difference')[:10]

    # O'qituvchilar bo'yicha statistika
    teacher_stats = recommendations.values(
        'submission__assignment__lesson__course__teacher__username',
        'submission__assignment__lesson__course__teacher__first_name',
        'submission__assignment__lesson__course__teacher__last_name',
    ).annotate(
        total=Count('id'),
        avg_diff=Avg('score_difference'),
        avg_ai=Avg('ai_score'),
        avg_teacher=Avg('teacher_score')
    ).order_by('-avg_diff')[:10]

    # Filter
    filter_type = request.GET.get('filter')
    if filter_type == 'high_difference':
        recommendations = recommendations.filter(score_difference__gte=20)
    elif filter_type == 'low_difference':
        recommendations = recommendations.filter(score_difference__lt=10)

    # Paginate
    paginator = Paginator(recommendations, 20)
    page = request.GET.get('page')
    recommendations = paginator.get_page(page)

    context = {
        'recommendations': recommendations,
        'total_graded': total_graded,
        'avg_ai_score': round(avg_ai_score, 1),
        'avg_teacher_score': round(avg_teacher_score, 1),
        'avg_difference': round(avg_difference, 1),
        'large_differences': large_differences,
        'teacher_stats': teacher_stats,
        'current_filter': filter_type,
    }
    return render(request, 'courses/supervisor/dashboard.html', context)


@login_required
def supervisor_recommendation_detail(request, pk):
    """Nazoratchi: AI recommendation batafsil"""
    from .models import AIGradeRecommendation

    if not _require_supervisor(request):
        return redirect('dashboard')

    recommendation = get_object_or_404(
        AIGradeRecommendation.objects.select_related(
            'submission',
            'submission__student',
            'submission__assignment',
            'submission__assignment__lesson__course__teacher'
        ),
        pk=pk
    )

    context = {
        'recommendation': recommendation,
        'submission': recommendation.submission,
        'assignment': recommendation.submission.assignment,
    }
    return render(request, 'courses/supervisor/recommendation_detail.html', context)


# ========================================
# GAME ARENA
# ========================================
@login_required
def game_arena(request):
    top_scores = {}
    for game_type, label in GameScore.GAME_TYPES:
        top_scores[game_type] = GameScore.objects.filter(
            game_type=game_type
        ).select_related('user').order_by('-score')[:10]

    user_best = {}
    for game_type, label in GameScore.GAME_TYPES:
        best = GameScore.objects.filter(
            user=request.user, game_type=game_type
        ).order_by('-score').first()
        user_best[game_type] = best

    context = {
        'top_scores': top_scores,
        'user_best': user_best,
    }
    return render(request, 'courses/game_arena/arena.html', context)


@login_required
def typing_game(request):
    difficulty = request.GET.get('difficulty', 'easy')
    texts = TypingText.objects.filter(is_active=True, difficulty=difficulty)
    text = texts.order_by('?').first()
    difficulties = TypingText.objects.filter(is_active=True).values_list('difficulty', flat=True).distinct()
    context = {
        'text': text,
        'difficulty': difficulty,
        'difficulties': list(difficulties),
    }
    return render(request, 'courses/game_arena/typing.html', context)


@login_required
def typing_game_submit(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    wpm = int(data.get('wpm', 0))
    accuracy = float(data.get('accuracy', 0))
    time_spent = int(data.get('time_spent', 0))

    # XP hisoblash
    xp = 0
    if wpm >= 100:
        xp = 40
    elif wpm >= 70:
        xp = 25
    elif wpm >= 50:
        xp = 15
    elif wpm >= 30:
        xp = 10

    # Accuracy bonus
    if accuracy >= 95:
        xp = int(xp * 1.2)

    score = int(wpm * (accuracy / 100))

    game_score = GameScore.objects.create(
        user=request.user,
        game_type='typing',
        score=score,
        details={'wpm': wpm, 'accuracy': accuracy, 'time_spent': time_spent},
        xp_earned=xp
    )

    if xp > 0:
        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(xp, f"Typing o'yini: {wpm} WPM")

    return JsonResponse({
        'success': True,
        'score': score,
        'xp_earned': xp,
        'wpm': wpm,
        'accuracy': accuracy,
    })


@login_required
def code_challenge_list(request):
    difficulty = request.GET.get('difficulty', '')
    challenges = CodeChallenge.objects.filter(is_active=True)
    if difficulty:
        challenges = challenges.filter(difficulty=difficulty)

    # Foydalanuvchi yechgan masalalar
    solved_ids = GameScore.objects.filter(
        user=request.user, game_type='code', details__solved=True
    ).values_list('details__challenge_id', flat=True)

    context = {
        'challenges': challenges,
        'difficulty': difficulty,
        'solved_ids': list(solved_ids),
    }
    return render(request, 'courses/game_arena/code_list.html', context)


@login_required
def code_challenge_play(request, pk):
    challenge = get_object_or_404(CodeChallenge, pk=pk, is_active=True)
    context = {
        'challenge': challenge,
    }
    return render(request, 'courses/game_arena/code_play.html', context)


def _run_python_safe(code, input_data="", timeout_sec=5):
    """Python kodni xavfsiz muhitda ishga tushirish va natijani qaytarish"""
    import ast
    import contextlib
    import io

    try:
        tree = ast.parse(code, mode='exec')
    except SyntaxError as e:
        return {'success': False, 'error': f"SyntaxError: {e}"}

    # Xavfsizlik tekshiruvi
    blocked_names = {'eval', 'exec', 'open', '__import__', 'compile',
                     'globals', 'locals', 'getattr', 'setattr', 'delattr'}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return {'success': False, 'error': "import taqiqlangan"}
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in blocked_names:
                return {'success': False, 'error': f"'{node.func.id}' funksiyasi taqiqlangan"}
        if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
            return {'success': False, 'error': "Maxsus atributlar taqiqlangan"}

    # input() funksiyasi uchun mock
    input_lines = input_data.strip().split('\n') if input_data.strip() else []
    input_idx = [0]

    def mock_input(prompt=""):
        if input_idx[0] < len(input_lines):
            val = input_lines[input_idx[0]]
            input_idx[0] += 1
            return val
        return ""

    safe_builtins = {
        'print': print, 'len': len, 'range': range, 'min': min, 'max': max,
        'sum': sum, 'abs': abs, 'round': round, 'sorted': sorted, 'reversed': reversed,
        'str': str, 'int': int, 'float': float, 'bool': bool,
        'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
        'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
        'input': mock_input, 'isinstance': isinstance, 'type': type,
        'chr': chr, 'ord': ord, 'hex': hex, 'bin': bin, 'oct': oct,
        'pow': pow, 'divmod': divmod, 'any': any, 'all': all,
    }

    output_stream = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_stream):
            exec(compile(tree, '<code>', 'exec'), {'__builtins__': safe_builtins}, {})
        output = output_stream.getvalue().strip()
        return {'success': True, 'output': output}
    except Exception as e:
        return {'success': False, 'error': f"{type(e).__name__}: {e}"}


@login_required
def code_challenge_run(request):
    """Kodni test case'lar bilan server-side ishga tushirish (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    challenge_id = data.get('challenge_id')
    user_code = data.get('code', '')

    challenge = get_object_or_404(CodeChallenge, pk=challenge_id, is_active=True)
    test_cases = challenge.test_cases or []

    results = []
    passed = 0
    for i, tc in enumerate(test_cases):
        input_data = tc.get('input', '')
        expected = str(tc.get('expected', '')).strip()

        result = _run_python_safe(user_code, input_data)

        if result['success']:
            actual = result['output']
            is_pass = actual == expected
            if is_pass:
                passed += 1
            results.append({
                'index': i + 1,
                'passed': is_pass,
                'expected': expected,
                'actual': actual,
                'error': None,
            })
        else:
            results.append({
                'index': i + 1,
                'passed': False,
                'expected': expected,
                'actual': None,
                'error': result['error'],
            })

    return JsonResponse({
        'success': True,
        'results': results,
        'passed': passed,
        'total': len(test_cases),
    })


@login_required
def code_challenge_submit(request):
    """Kodni serverda tekshirib natija saqlash (AJAX)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    challenge_id = data.get('challenge_id')
    user_code = data.get('code', '')
    time_spent = int(data.get('time_spent', 0))

    challenge = get_object_or_404(CodeChallenge, pk=challenge_id, is_active=True)
    test_cases = challenge.test_cases or []

    # Server-side real tekshiruv
    passed_tests = 0
    total_tests = len(test_cases)
    for tc in test_cases:
        input_data = tc.get('input', '')
        expected = str(tc.get('expected', '')).strip()
        result = _run_python_safe(user_code, input_data)
        if result['success'] and result['output'] == expected:
            passed_tests += 1

    all_passed = passed_tests == total_tests and total_tests > 0

    xp = 0
    if all_passed:
        xp_map = {'easy': 20, 'medium': 35, 'hard': 50}
        xp = xp_map.get(challenge.difficulty, 20)

    score = int((passed_tests / max(total_tests, 1)) * 100)

    GameScore.objects.create(
        user=request.user,
        game_type='code',
        score=score,
        details={
            'challenge_id': challenge_id,
            'solved': all_passed,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'time_spent': time_spent,
        },
        xp_earned=xp
    )

    if xp > 0:
        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(xp, f"Kod masala: {challenge.title}")

    return JsonResponse({
        'success': True,
        'all_passed': all_passed,
        'passed_tests': passed_tests,
        'total_tests': total_tests,
        'score': score,
        'xp_earned': xp,
    })


@login_required
def math_game(request):
    return render(request, 'courses/game_arena/math.html')


@login_required
def math_game_submit(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    correct = int(data.get('correct', 0))
    total = int(data.get('total', 0))
    time_spent = int(data.get('time_spent', 0))
    difficulty = data.get('difficulty', 'easy')

    # XP: har 5 to'g'ri javob = 10 XP
    xp = (correct // 5) * 10

    score = correct

    GameScore.objects.create(
        user=request.user,
        game_type='math',
        score=score,
        details={
            'correct': correct,
            'total': total,
            'time_spent': time_spent,
            'difficulty': difficulty,
        },
        xp_earned=xp
    )

    if xp > 0:
        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(xp, f"Math quiz: {correct}/{total} to'g'ri")

    return JsonResponse({
        'success': True,
        'score': score,
        'xp_earned': xp,
        'correct': correct,
        'total': total,
    })


@login_required
def memory_game(request):
    import json as _json
    cards = list(
        MemoryCard.objects.filter(is_active=True)
            .order_by('?')[:8]
            .values('id', 'term', 'match')
    )
    context = {
        'cards_json': _json.dumps(cards, ensure_ascii=False),
        'total_pairs': len(cards),
    }
    return render(request, 'courses/game_arena/memory.html', context)


@login_required
def memory_game_submit(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    time_spent = int(data.get('time_spent', 0))
    moves = int(data.get('moves', 0))
    pairs = int(data.get('pairs', 0))

    # XP tezlikka qarab
    xp = 0
    if time_spent <= 30:
        xp = 30
    elif time_spent <= 60:
        xp = 20
    elif time_spent <= 120:
        xp = 10
    else:
        xp = 5

    score = max(0, 1000 - (time_spent * 5) - (moves * 2))

    GameScore.objects.create(
        user=request.user,
        game_type='memory',
        score=score,
        details={
            'time_spent': time_spent,
            'moves': moves,
            'pairs': pairs,
        },
        xp_earned=xp
    )

    if xp > 0:
        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        xp_profile.add_xp(xp, f"Memory o'yini: {time_spent}s, {moves} harakat")

    return JsonResponse({
        'success': True,
        'score': score,
        'xp_earned': xp,
        'time_spent': time_spent,
        'moves': moves,
    })


@login_required
def game_leaderboard(request, game_type):
    valid_types = dict(GameScore.GAME_TYPES)
    if game_type not in valid_types:
        return redirect('game_arena')

    scores = GameScore.objects.filter(
        game_type=game_type
    ).select_related('user').order_by('-score')[:50]

    user_best = GameScore.objects.filter(
        user=request.user, game_type=game_type
    ).order_by('-score').first()

    context = {
        'scores': scores,
        'game_type': game_type,
        'game_name': valid_types[game_type],
        'user_best': user_best,
    }
    return render(request, 'courses/game_arena/leaderboard.html', context)
