from django.contrib import admin
from .models import (
    Category, Course, Lesson, Enrollment, LessonProgress,
    Quiz, Question, Answer, QuizAttempt, QuizResponse,
    Assignment, Submission, Certificate, CourseReview,
    Discussion, Reply, Notification, Payment, PromoCode,
    Wishlist, CourseCompletion, Badge, UserBadge, UserXP,
    XPTransaction, DailyChallenge, UserChallenge, ChatMessage,
    TelegramUser, AIGradeRecommendation,
    TypingText, CodeChallenge, GameScore, MemoryCard
)


# ========================================
# CATEGORY
# ========================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


# ========================================
# COURSE
# ========================================
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['title', 'lesson_type', 'duration', 'order', 'is_published', 'is_free']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'teacher', 'category', 'level', 'price', 'is_published', 'is_featured', 'average_rating', 'total_students']
    list_filter = ['is_published', 'is_featured', 'is_free', 'level', 'category']
    search_fields = ['title', 'description', 'teacher__username']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_published', 'is_featured']
    inlines = [LessonInline]
    date_hierarchy = 'created_at'


# ========================================
# LESSON
# ========================================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'lesson_type', 'duration', 'order', 'is_published', 'is_free', 'xp_reward']
    list_filter = ['lesson_type', 'is_published', 'is_free', 'course']
    search_fields = ['title', 'course__title']
    list_editable = ['order', 'is_published', 'is_free']
    ordering = ['course', 'order']


# ========================================
# ENROLLMENT
# ========================================
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'enrolled_at', 'progress', 'completed']
    list_filter = ['completed', 'enrolled_at']
    search_fields = ['student__username', 'course__title']
    date_hierarchy = 'enrolled_at'


# ========================================
# LESSON PROGRESS
# ========================================
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'completed', 'completed_at']
    list_filter = ['completed']
    search_fields = ['student__username', 'lesson__title']


# ========================================
# QUIZ
# ========================================
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'time_limit', 'passing_score', 'max_attempts', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title']
    inlines = [QuestionInline]


# ========================================
# QUESTION
# ========================================
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'quiz', 'question_type', 'points', 'order']
    list_filter = ['question_type', 'quiz']
    search_fields = ['text']
    inlines = [AnswerInline]


# ========================================
# ANSWER
# ========================================
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'is_correct', 'order']
    list_filter = ['is_correct']
    search_fields = ['text']


# ========================================
# QUIZ ATTEMPT
# ========================================
@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'passed', 'started_at', 'completed_at']
    list_filter = ['passed', 'quiz']
    search_fields = ['student__username', 'quiz__title']
    date_hierarchy = 'started_at'


# ========================================
# QUIZ RESPONSE
# ========================================
@admin.register(QuizResponse)
class QuizResponseAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'is_correct']
    list_filter = ['is_correct']


# ========================================
# ASSIGNMENT
# ========================================
@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson', 'max_score', 'due_days', 'created_at']
    list_filter = ['lesson__course']
    search_fields = ['title']


# ========================================
# SUBMISSION
# ========================================
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'assignment', 'submitted_at', 'score', 'is_graded']
    list_filter = ['is_graded', 'assignment']
    search_fields = ['student__username', 'assignment__title']
    date_hierarchy = 'submitted_at'


# ========================================
# CERTIFICATE
# ========================================
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'student', 'course', 'issued_at']
    list_filter = ['course']
    search_fields = ['certificate_number', 'student__username', 'course__title']
    date_hierarchy = 'issued_at'


# ========================================
# COURSE REVIEW
# ========================================
@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'course']
    search_fields = ['user__username', 'course__title', 'content']
    list_editable = ['is_approved']
    date_hierarchy = 'created_at'


# ========================================
# DISCUSSION
# ========================================
@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'author', 'is_pinned', 'is_closed', 'views_count', 'created_at']
    list_filter = ['is_pinned', 'is_closed', 'course']
    search_fields = ['title', 'author__username']
    list_editable = ['is_pinned', 'is_closed']


# ========================================
# REPLY
# ========================================
@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ['author', 'discussion', 'is_solution', 'likes_count', 'created_at']
    list_filter = ['is_solution']
    search_fields = ['author__username', 'content']


# ========================================
# NOTIFICATION
# ========================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['recipient__username', 'title']
    date_hierarchy = 'created_at'


# ========================================
# PAYMENT
# ========================================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['student__username', 'course__title', 'transaction_id']
    date_hierarchy = 'created_at'


# ========================================
# PROMO CODE
# ========================================
@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_until', 'is_active', 'current_uses', 'max_uses']
    list_filter = ['is_active', 'discount_type']
    search_fields = ['code']
    list_editable = ['is_active']


# ========================================
# WISHLIST
# ========================================
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'added_at']
    search_fields = ['user__username', 'course__title']


# ========================================
# COURSE COMPLETION
# ========================================
@admin.register(CourseCompletion)
class CourseCompletionAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'completed_at']
    search_fields = ['student__username', 'course__title']


# ========================================
# BADGE
# ========================================
@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'badge_type', 'icon', 'xp_reward', 'is_active']
    list_filter = ['badge_type', 'is_active']
    search_fields = ['name']


# ========================================
# USER BADGE
# ========================================
@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge']
    search_fields = ['user__username', 'badge__name']


# ========================================
# USER XP
# ========================================
@admin.register(UserXP)
class UserXPAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_xp', 'level', 'current_streak', 'longest_streak']
    search_fields = ['user__username']
    ordering = ['-total_xp']


# ========================================
# XP TRANSACTION
# ========================================
@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'description']
    date_hierarchy = 'created_at'


# ========================================
# DAILY CHALLENGE
# ========================================
@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'xp_reward', 'is_active']
    list_filter = ['is_active', 'date']
    search_fields = ['title']


# ========================================
# USER CHALLENGE
# ========================================
@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'completed_at']
    search_fields = ['user__username']


# ========================================
# CHAT MESSAGE
# ========================================
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'message', 'created_at']
    list_filter = ['course']
    search_fields = ['user__username', 'message']
    date_hierarchy = 'created_at'


# ========================================
# TELEGRAM USER
# ========================================
@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_id', 'username', 'is_active', 'notifications_enabled', 'created_at']
    list_filter = ['is_active', 'notifications_enabled']
    search_fields = ['user__username', 'username', 'telegram_id']


# ========================================
# AI GRADE RECOMMENDATION
# ========================================
@admin.register(AIGradeRecommendation)
class AIGradeRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'submission_student', 'submission_assignment', 'ai_score', 'teacher_score',
        'supervisor_score', 'supervisor_status', 'score_difference', 'is_reviewed', 'created_at',
    ]
    list_filter = ['is_reviewed', 'supervisor_status', 'created_at']
    search_fields = ['submission__student__username', 'submission__assignment__title']
    readonly_fields = ['created_at', 'reviewed_at', 'supervisor_reviewed_at']

    def submission_student(self, obj):
        return obj.submission.student.username
    submission_student.short_description = 'Talaba'

    def submission_assignment(self, obj):
        return obj.submission.assignment.title
    submission_assignment.short_description = 'Topshiriq'


# ========================================
# GAME ARENA
# ========================================
@admin.register(TypingText)
class TypingTextAdmin(admin.ModelAdmin):
    list_display = ['text_short', 'difficulty', 'language', 'is_active']
    list_filter = ['difficulty', 'language', 'is_active']
    list_editable = ['is_active']

    def text_short(self, obj):
        return obj.text[:80]
    text_short.short_description = 'Matn'


@admin.register(CodeChallenge)
class CodeChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'xp_reward', 'time_limit', 'is_active']
    list_filter = ['difficulty', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['is_active']


@admin.register(GameScore)
class GameScoreAdmin(admin.ModelAdmin):
    list_display = ['user', 'game_type', 'score', 'xp_earned', 'played_at']
    list_filter = ['game_type', 'played_at']
    search_fields = ['user__username']
    date_hierarchy = 'played_at'


@admin.register(MemoryCard)
class MemoryCardAdmin(admin.ModelAdmin):
    list_display = ['term', 'match', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['term', 'match']
    list_editable = ['is_active']
