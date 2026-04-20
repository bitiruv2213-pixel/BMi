from datetime import timedelta
import secrets

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
from .forms import (
    UserRegisterForm, UserLoginForm, UserUpdateForm,
    ProfileUpdateForm, CustomPasswordChangeForm,
    PasswordResetRequestForm, PasswordResetCodeConfirmForm,
)
from .models import PasswordResetCode, Profile
from .role_utils import is_teacher


PASSWORD_RESET_CODE_TTL_MINUTES = 10


def _generate_password_reset_code():
    return f"{secrets.randbelow(1000000):06d}"


def _mask_email(email):
    if not email or '@' not in email:
        return email
    local_part, domain = email.split('@', 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + '*'
    else:
        masked_local = local_part[:2] + '*' * max(1, len(local_part) - 2)
    return f"{masked_local}@{domain}"


def _create_password_reset_code(user):
    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    code = _generate_password_reset_code()
    reset_code = PasswordResetCode(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=PASSWORD_RESET_CODE_TTL_MINUTES),
    )
    reset_code.set_code(code)
    reset_code.save()
    return code


def _send_password_reset_code(user, raw_code):
    subject = "LMS Platform - Parolni tiklash kodi"
    message = (
        f"Salom, {user.get_full_name() or user.username}!\n\n"
        f"Parolni tiklash uchun tasdiqlash kodingiz: {raw_code}\n\n"
        f"Kod {PASSWORD_RESET_CODE_TTL_MINUTES} daqiqa amal qiladi.\n"
        "Agar bu so'rov siz tomondan yuborilmagan bo'lsa, ushbu emailni e'tiborsiz qoldiring."
    )
    send_mail(
        subject,
        message,
        getattr(django_settings, 'DEFAULT_FROM_EMAIL', 'noreply@lms.uz'),
        [user.email],
        fail_silently=False,
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    google_login_available = bool(
        getattr(django_settings, 'GOOGLE_CLIENT_ID', '')
        and getattr(django_settings, 'GOOGLE_CLIENT_SECRET', '')
    )

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Xush kelibsiz, {user.first_name}! Ro'yxatdan muvaffaqiyatli o'tdingiz.")
            return redirect('dashboard')
        else:
            messages.error(request, "Ro'yxatdan o'tishda xatolik yuz berdi.")
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'google_login_available': google_login_available,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    google_login_available = bool(
        getattr(django_settings, 'GOOGLE_CLIENT_ID', '')
        and getattr(django_settings, 'GOOGLE_CLIENT_SECRET', '')
    )

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Xush kelibsiz, {user.first_name or user.username}!")

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, "Login yoki parol noto'g'ri!")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'google_login_available': google_login_available,
    })


def password_reset_request_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            user = User.objects.filter(email__iexact=email).first()
            if user and user.email:
                code = _create_password_reset_code(user)
                _send_password_reset_code(user, code)
                request.session['password_reset_email'] = user.email
            return redirect('password_reset_done')
    else:
        form = PasswordResetRequestForm(initial={
            'email': request.session.get('password_reset_email', ''),
        })

    return render(request, 'accounts/password_reset.html', {'form': form})


def password_reset_done_view(request):
    email = request.session.get('password_reset_email', '')
    return render(request, 'accounts/password_reset_done.html', {
        'masked_email': _mask_email(email) if email else '',
        'code_ttl_minutes': PASSWORD_RESET_CODE_TTL_MINUTES,
    })


def password_reset_confirm_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    initial_email = request.session.get('password_reset_email', '')
    if request.method == 'POST':
        form = PasswordResetCodeConfirmForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            code = form.cleaned_data['code']
            password = form.cleaned_data['new_password1']
            user = User.objects.filter(email__iexact=email).first()
            reset_code = None
            if user:
                reset_code = user.password_reset_codes.filter(used_at__isnull=True).order_by('-created_at').first()

            if not user or not reset_code or not reset_code.verify_code(code):
                form.add_error('code', "Kod noto'g'ri yoki muddati tugagan.")
            else:
                user.set_password(password)
                user.save(update_fields=['password'])
                reset_code.mark_used()
                request.session.pop('password_reset_email', None)
                messages.success(request, "Parol muvaffaqiyatli yangilandi.")
                return redirect('password_reset_complete')
    else:
        form = PasswordResetCodeConfirmForm(initial={'email': initial_email})

    return render(request, 'accounts/password_reset_confirm.html', {
        'form': form,
        'code_ttl_minutes': PASSWORD_RESET_CODE_TTL_MINUTES,
    })


def password_reset_complete_view(request):
    return render(request, 'accounts/password_reset_complete.html')


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz.")
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user

    # Ensure profile exists
    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user)

    # Get user statistics
    from courses.models import Enrollment, Certificate, UserXP, UserBadge, LessonProgress

    enrollments = Enrollment.objects.filter(student=user)
    certificates = Certificate.objects.filter(student=user)

    try:
        xp_profile = UserXP.objects.get(user=user)
    except UserXP.DoesNotExist:
        xp_profile = UserXP.objects.create(user=user)

    user_badges = UserBadge.objects.filter(user=user).select_related('badge')[:6]

    # Calculate stats
    completed_lessons = LessonProgress.objects.filter(student=user, completed=True).count()

    context = {
        'profile_user': user,
        'total_courses': enrollments.count(),
        'completed_courses': enrollments.filter(completed=True).count(),
        'certificates_count': certificates.count(),
        'xp_profile': xp_profile,
        'user_badges': user_badges,
        'completed_lessons': completed_lessons,
        'recent_enrollments': enrollments.order_by('-enrolled_at')[:5],
        'certificates': certificates.order_by('-issued_at')[:3],
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    user = request.user

    # Ensure profile exists
    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profil muvaffaqiyatli yangilandi!")
            return redirect('profile')
        else:
            messages.error(request, "Xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring.")
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Parol muvaffaqiyatli o'zgartirildi!")
            return redirect('profile')
        else:
            messages.error(request, "Xatolik yuz berdi.")
    else:
        form = CustomPasswordChangeForm(request.user)

    return render(request, 'accounts/password_change.html', {'form': form})


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(username=request.user.username, password=password)

        if user is not None:
            user.delete()
            messages.success(request, "Hisobingiz o'chirildi.")
            return redirect('login')
        else:
            messages.error(request, "Parol noto'g'ri!")

    return render(request, 'accounts/delete_account.html')


def public_profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)

    from courses.models import Enrollment, Certificate, UserXP, UserBadge, Course

    # Public stats only
    enrollments = Enrollment.objects.filter(student=profile_user)
    certificates = Certificate.objects.filter(student=profile_user)

    try:
        xp_profile = UserXP.objects.get(user=profile_user)
    except UserXP.DoesNotExist:
        xp_profile = None

    user_badges = UserBadge.objects.filter(user=profile_user).select_related('badge')[:6]

    # If teacher, show their courses
    teacher_courses = None
    if profile_user.profile.is_teacher:
        teacher_courses = Course.objects.filter(teacher=profile_user, is_published=True)[:6]

    context = {
        'profile_user': profile_user,
        'total_courses': enrollments.count(),
        'completed_courses': enrollments.filter(completed=True).count(),
        'certificates_count': certificates.count(),
        'xp_profile': xp_profile,
        'user_badges': user_badges,
        'teacher_courses': teacher_courses,
        'is_own_profile': request.user == profile_user,
    }
    return render(request, 'accounts/public_profile.html', context)


# ==================== TEACHER VIEWS ====================

@login_required
def teacher_dashboard(request):
    """O'qituvchi dashboard"""
    if not is_teacher(request.user):
        messages.error(request, "Bu sahifa faqat o'qituvchilar uchun!")
        return redirect('dashboard')

    return redirect('teacher_dashboard')

    # O'qituvchining kurslari
    courses = Course.objects.filter(teacher=request.user).annotate(
        students_count=Count('enrollments', distinct=True),
        avg_rating=Avg('reviews__rating')
    ).order_by('-created_at')

    # Statistika
    total_courses = courses.count()
    total_students = Enrollment.objects.filter(course__teacher=request.user).count()
    total_revenue = 0  # Keyin qo'shish mumkin

    # Oxirgi yozilganlar
    recent_enrollments = Enrollment.objects.filter(
        course__teacher=request.user
    ).select_related('student', 'course').order_by('-enrolled_at')[:5]

    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_revenue': total_revenue,
        'recent_enrollments': recent_enrollments,
    }
    return render(request, 'accounts/teacher_dashboard.html', context)


@login_required
def teacher_my_courses(request):
    """O'qituvchining barcha kurslari"""
    if not is_teacher(request.user):
        messages.error(request, "Bu sahifa faqat o'qituvchilar uchun!")
        return redirect('dashboard')

    return redirect('teacher_courses')


@login_required
def teacher_course_students(request, course_slug):
    """Kursga yozilgan talabalar ro'yxati"""
    if not is_teacher(request.user):
        messages.error(request, "Bu sahifa faqat o'qituvchilar uchun!")
        return redirect('dashboard')

    return redirect('teacher_course_students', slug=course_slug)


@login_required
def teacher_student_detail(request, course_slug, user_id):
    """Alohida talabaning kurs bo'yicha progressi"""
    if not is_teacher(request.user):
        messages.error(request, "Bu sahifa faqat o'qituvchilar uchun!")
        return redirect('dashboard')

    return redirect('teacher_student_detail', course_slug=course_slug, user_id=user_id)
