from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Course, Lesson, Enrollment,
    Quiz, Question, Answer, QuizAttempt,
    Certificate, CourseReview, UserXP, Badge, UserBadge
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name()


class CategorySerializer(serializers.ModelSerializer):
    courses_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'courses_count']

    def get_courses_count(self, obj):
        return obj.courses.filter(is_published=True).count()


class LessonListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'lesson_type', 'duration', 'order', 'is_free', 'xp_reward']


class LessonDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'content', 'lesson_type',
                  'video_url', 'duration', 'order', 'is_free', 'xp_reward']


class CourseListSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'short_description', 'thumbnail',
                  'teacher', 'category', 'level', 'is_free', 'price',
                  'average_rating', 'total_reviews']


class CourseDetailSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    lessons = LessonListSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'short_description',
                  'thumbnail', 'teacher', 'category', 'level', 'language',
                  'is_free', 'price', 'discount_price',
                  'average_rating', 'total_reviews',
                  'lessons', 'is_enrolled', 'created_at']

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(student=request.user, course=obj).exists()
        return False


class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'progress', 'completed', 'completed_at']


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'image', 'points', 'order', 'answers']


class QuizSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'time_limit', 'passing_score',
                  'max_attempts', 'xp_reward', 'questions_count']

    def get_questions_count(self, obj):
        return obj.questions.count()


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'time_limit', 'passing_score',
                  'max_attempts', 'xp_reward', 'questions']


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz = QuizSerializer(read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'started_at', 'completed_at', 'score',
                  'passed', 'time_spent', 'xp_earned', 'correct_answers', 'wrong_answers']


class CertificateSerializer(serializers.ModelSerializer):
    course = CourseListSerializer(read_only=True)

    class Meta:
        model = Certificate
        fields = ['id', 'certificate_number', 'course', 'issued_at']


class CourseReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CourseReview
        fields = ['id', 'user', 'rating', 'title', 'content', 'helpful_count',
                  'instructor_response', 'created_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseReview
        fields = ['rating', 'title', 'content']


class UserXPSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserXP
        fields = ['total_xp', 'level', 'current_streak', 'longest_streak']


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['id', 'name', 'description', 'icon', 'color', 'badge_type', 'xp_reward']


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ['badge', 'earned_at']


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name()
