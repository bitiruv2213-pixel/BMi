from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
import uuid


# ========================================
# CATEGORY
# ========================================
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ========================================
# COURSE
# ========================================
class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Boshlang\'ich'),
        ('intermediate', 'O\'rta'),
        ('advanced', 'Yuqori'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500, blank=True)
    thumbnail = models.FileField(upload_to='courses/thumbnails/', blank=True, null=True)

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_teaching')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    language = models.CharField(max_length=50, default="O'zbek")

    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    discount_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    requirements = models.TextField(blank=True)
    what_you_learn = models.TextField(blank=True)

    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Course.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        if self.is_free:
            return 0
        return self.discount_price if self.discount_price else self.price

    @property
    def total_lessons(self):
        return self.lessons.filter(is_published=True).count()

    @property
    def total_duration(self):
        return self.lessons.filter(is_published=True).aggregate(
            total=models.Sum('duration')
        )['total'] or 0


# ========================================
# LESSON
# ========================================
class Lesson(models.Model):
    LESSON_TYPE_CHOICES = [
        ('video', 'Video'),
        ('text', 'Matn'),
        ('quiz', 'Test'),
        ('assignment', 'Topshiriq'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content = models.TextField(blank=True)
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPE_CHOICES, default='video')

    video_url = models.URLField(blank=True)
    video_file = models.FileField(upload_to='courses/videos/', blank=True, null=True)
    attachment = models.FileField(upload_to='courses/attachments/', blank=True, null=True)

    duration = models.PositiveIntegerField(default=0, help_text="Daqiqalarda")
    order = models.PositiveIntegerField(default=1)

    is_free = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    xp_reward = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"
        ordering = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


# ========================================
# ENROLLMENT
# ========================================
class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    progress = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Yozilish"
        verbose_name_plural = "Yozilishlar"
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


# ========================================
# LESSON PROGRESS
# ========================================
class LessonProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    watch_time = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Dars progressi"
        verbose_name_plural = "Dars progresslari"
        unique_together = ['student', 'lesson']

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title}"


# ========================================
# QUIZ
# ========================================
class Quiz(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit = models.PositiveIntegerField(default=30, help_text="Daqiqalarda")
    passing_score = models.PositiveIntegerField(default=70)
    max_attempts = models.PositiveIntegerField(default=3)
    shuffle_questions = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=True)
    xp_reward = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    def __str__(self):
        return self.title


# ========================================
# QUESTION
# ========================================
class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('single', 'Bitta javob'),
        ('multiple', 'Ko\'p javob'),
        ('text', 'Matnli javob'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default='single')
    image = models.FileField(upload_to='quizzes/questions/', blank=True, null=True)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['order']

    def __str__(self):
        return self.text[:50]


# ========================================
# ANSWER
# ========================================
class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
        ordering = ['order']

    def __str__(self):
        return self.text[:50]


# ========================================
# QUIZ ATTEMPT
# ========================================
class QuizAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Test urinishi"
        verbose_name_plural = "Test urinishlari"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} - {self.score}%"


# ========================================
# QUIZ RESPONSE
# ========================================
class QuizResponse(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answers = models.CharField(max_length=500, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Test javobi"
        verbose_name_plural = "Test javoblari"

    def __str__(self):
        return f"{self.attempt.id} - {self.question.id}"


# ========================================
# ASSIGNMENT
# ========================================
class Assignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField(blank=True)
    max_score = models.PositiveIntegerField(default=100)
    due_days = models.PositiveIntegerField(default=7)
    attachment = models.FileField(upload_to='assignments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Topshiriq"
        verbose_name_plural = "Topshiriqlar"

    def __str__(self):
        return self.title


# ========================================
# SUBMISSION
# ========================================
class Submission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='graded_submissions')
    graded_at = models.DateTimeField(null=True, blank=True)
    is_graded = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Topshiriq javobi"
        verbose_name_plural = "Topshiriq javoblari"
        unique_together = ['student', 'assignment']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"


# ========================================
# CERTIFICATE
# ========================================
class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_number = models.CharField(max_length=50, unique=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = f"LMS-{timezone.now().strftime('%Y%m%d')}-{str(self.id)[:8].upper()}"
        super().save(*args, **kwargs)


# ========================================
# COURSE REVIEW
# ========================================
class CourseReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(default=5)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    helpful_count = models.PositiveIntegerField(default=0)
    instructor_response = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating}"


# ========================================
# DISCUSSION
# ========================================
class Discussion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='discussions')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discussions')
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Muhokama"
        verbose_name_plural = "Muhokamalar"
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


# ========================================
# REPLY
# ========================================
class Reply(models.Model):
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} - {self.discussion.title[:30]}"


# ========================================
# NOTIFICATION
# ========================================
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('enrollment', 'Yozilish'),
        ('completion', 'Tugatish'),
        ('certificate', 'Sertifikat'),
        ('grade', 'Baho'),
        ('reply', 'Javob'),
        ('badge', 'Nishon'),
        ('xp', 'XP'),
        ('system', 'Tizim'),
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"


# ========================================
# PAYMENT
# ========================================
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('payme', 'Payme'),
        ('click', 'Click'),
        ('uzum', 'Uzum Bank'),
        ('manual', 'Qo\'lda'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('completed', 'Yakunlangan'),
        ('failed', 'Xato'),
        ('refunded', 'Qaytarilgan'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='payme')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.amount}"


# ========================================
# PROMO CODE
# ========================================
class PromoCode(models.Model):
    DISCOUNT_TYPES = [
        ('percent', 'Foiz'),
        ('fixed', 'Belgilangan'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_uses = models.PositiveIntegerField(default=100)
    current_uses = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    courses = models.ManyToManyField(Course, blank=True, related_name='promo_codes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Promo kod"
        verbose_name_plural = "Promo kodlar"

    def __str__(self):
        return self.code


# ========================================
# WISHLIST
# ========================================
class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Istaklar"
        verbose_name_plural = "Istaklar ro'yxati"
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


# ========================================
# COURSE COMPLETION
# ========================================
class CourseCompletion(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='completions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kurs tugatilishi"
        verbose_name_plural = "Kurs tugatilishlari"
        unique_together = ['student', 'course']

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


# ========================================
# BADGE
# ========================================
class Badge(models.Model):
    BADGE_TYPES = [
        ('course', 'Kurs'),
        ('streak', 'Streak'),
        ('xp', 'XP'),
        ('social', 'Ijtimoiy'),
        ('special', 'Maxsus'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='🏆')
    color = models.CharField(max_length=20, default='#FFD700')
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES, default='special')
    requirement_value = models.PositiveIntegerField(default=0)
    xp_reward = models.PositiveIntegerField(default=25)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nishon"
        verbose_name_plural = "Nishonlar"

    def __str__(self):
        return self.name


# ========================================
# USER BADGE
# ========================================
class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='users')
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foydalanuvchi nishoni"
        verbose_name_plural = "Foydalanuvchi nishonlari"
        unique_together = ['user', 'badge']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


# ========================================
# USER XP
# ========================================
class UserXP(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_profile')
    total_xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Foydalanuvchi XP"
        verbose_name_plural = "Foydalanuvchi XPlari"

    def __str__(self):
        return f"{self.user.username} - {self.total_xp} XP"

    def add_xp(self, amount, description=""):
        self.total_xp = max(0, self.total_xp + amount)
        self.level = self.calculate_level()
        if amount > 0:
            self.update_streak()
        self.save()

        XPTransaction.objects.create(
            user=self.user,
            amount=amount,
            description=description
        )

    def calculate_level(self):
        # Har 100 XP uchun 1 level
        return (self.total_xp // 100) + 1

    def update_streak(self):
        today = timezone.now().date()
        if self.last_activity_date:
            diff = (today - self.last_activity_date).days
            if diff == 1:
                self.current_streak += 1
            elif diff > 1:
                self.current_streak = 1
        else:
            self.current_streak = 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_activity_date = today

    @property
    def xp_for_next_level(self):
        next_level_xp = self.level * 100
        return next_level_xp - self.total_xp

    @property
    def level_progress(self):
        level_start = (self.level - 1) * 100
        level_end = self.level * 100
        progress = ((self.total_xp - level_start) / (level_end - level_start)) * 100
        return min(100, max(0, progress))


# ========================================
# XP TRANSACTION
# ========================================
class XPTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='xp_transactions')
    amount = models.IntegerField()
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "XP tranzaksiya"
        verbose_name_plural = "XP tranzaksiyalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.amount} XP"


# ========================================
# DAILY CHALLENGE
# ========================================
class DailyChallenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=50)
    target_value = models.PositiveIntegerField(default=1)
    xp_reward = models.PositiveIntegerField(default=20)
    date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Kunlik topshiriq"
        verbose_name_plural = "Kunlik topshiriqlar"

    def __str__(self):
        return f"{self.title} - {self.date}"


# ========================================
# USER CHALLENGE
# ========================================
class UserChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='challenges')
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Foydalanuvchi topshirig'i"
        verbose_name_plural = "Foydalanuvchi topshiriqlari"
        unique_together = ['user', 'challenge']

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}"


# ========================================
# CHAT MESSAGE
# ========================================
class ChatMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_messages')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Chat xabar"
        verbose_name_plural = "Chat xabarlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"


# ========================================
# TELEGRAM USER
# ========================================
class TelegramUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='telegram')
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=100, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram foydalanuvchi"
        verbose_name_plural = "Telegram foydalanuvchilar"

    def __str__(self):
        return f"{self.user.username} - {self.telegram_id}"


class AIGradeRecommendation(models.Model):
    """AI tomonidan topshiriq uchun tavsiya etilgan baho"""
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='ai_recommendation')

    # AI tahlili
    ai_score = models.IntegerField(help_text="AI tavsiya etgan ball")
    max_score = models.IntegerField(help_text="Maksimal ball")
    confidence = models.FloatField(default=0.0, help_text="AI ishonch darajasi (0-1)")

    # Tahlil detallari
    analysis = models.TextField(help_text="AI tahlili va izohlar")
    strengths = models.TextField(blank=True, help_text="Kuchli tomonlar")
    weaknesses = models.TextField(blank=True, help_text="Zaif tomonlar")
    suggestions = models.TextField(blank=True, help_text="Yaxshilash bo'yicha takliflar")

    # O'qituvchi bahosi
    teacher_score = models.IntegerField(null=True, blank=True, help_text="O'qituvchi qo'ygan ball")
    teacher_feedback = models.TextField(blank=True, help_text="O'qituvchi izohi")

    # Farq tahlili
    score_difference = models.IntegerField(default=0, help_text="AI va o'qituvchi baho farqi")
    is_reviewed = models.BooleanField(default=False, help_text="O'qituvchi ko'rib chiqdi")

    # Vaqt
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "AI Baho Tavsiyasi"
        verbose_name_plural = "AI Baho Tavsiялari"
        ordering = ['-created_at']

    def __str__(self):
        return f"AI: {self.ai_score}/{self.max_score} - {self.submission.student.username}"

    def calculate_difference(self):
        """O'qituvchi baho qo'ygandan keyin farqni hisoblash"""
        if self.teacher_score:
            self.score_difference = abs(self.teacher_score - self.ai_score)
            self.save()


# ========================================
# GAME ARENA MODELS
# ========================================
class TypingText(models.Model):
    """Tez yozish o'yini uchun matnlar"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Oson'),
        ('medium', "O'rta"),
        ('hard', 'Qiyin'),
    ]
    text = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='easy')
    language = models.CharField(max_length=20, default='uz')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Typing matn"
        verbose_name_plural = "Typing matnlar"

    def __str__(self):
        return self.text[:50]


class CodeChallenge(models.Model):
    """Kod yozish o'yini uchun masalalar"""
    DIFFICULTY_CHOICES = [
        ('easy', 'Oson'),
        ('medium', "O'rta"),
        ('hard', 'Qiyin'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='easy')
    initial_code = models.TextField(blank=True)
    solution = models.TextField()
    test_cases = models.JSONField(default=list)
    time_limit = models.PositiveIntegerField(default=300)
    xp_reward = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Kod masala"
        verbose_name_plural = "Kod masalalar"

    def __str__(self):
        return self.title


class GameScore(models.Model):
    """Barcha o'yinlar uchun umumiy natijalar jadvali"""
    GAME_TYPES = [
        ('typing', 'Tez yozish'),
        ('code', 'Kod yozish'),
        ('math', 'Matematik'),
        ('memory', 'Xotira'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_scores')
    game_type = models.CharField(max_length=20, choices=GAME_TYPES)
    score = models.PositiveIntegerField(default=0)
    details = models.JSONField(default=dict)
    xp_earned = models.PositiveIntegerField(default=0)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O'yin natijasi"
        verbose_name_plural = "O'yin natijalari"
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.user.username} - {self.game_type} - {self.score}"


class MemoryCard(models.Model):
    """Memory o'yini uchun karta juftliklari"""
    term = models.CharField(max_length=100)
    match = models.CharField(max_length=100)
    category = models.CharField(max_length=50, default='programming', choices=[
        ('programming', 'Dasturlash'),
        ('python', 'Python'),
        ('web', 'Veb'),
        ('database', 'Ma\'lumotlar bazasi'),
        ('general', 'Umumiy IT'),
    ])
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Memory karta"
        verbose_name_plural = "Memory kartalar"

    def __str__(self):
        return f"{self.term} ↔ {self.match}"
