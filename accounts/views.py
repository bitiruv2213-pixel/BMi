from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q
from django.conf import settings as django_settings
from .forms import (
    UserRegisterForm, UserLoginForm, UserUpdateForm,
    ProfileUpdateForm, CustomPasswordChangeForm
)
from .models import Profile
from .role_utils import is_teacher


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
