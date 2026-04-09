from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Category, Course, Lesson, Enrollment, LessonProgress,
    Quiz, QuizAttempt, Certificate, CourseReview, UserXP
)
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    LessonDetailSerializer, EnrollmentSerializer, QuizSerializer,
    QuizDetailSerializer, QuizAttemptSerializer, CertificateSerializer,
    CourseReviewSerializer, ReviewCreateSerializer, UserProfileSerializer,
    UserXPSerializer
)


# CATEGORY API
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


# COURSE API
class CourseListView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True)

        category = self.request.query_params.get('category')
        level = self.request.query_params.get('level')
        is_free = self.request.query_params.get('is_free')
        search = self.request.query_params.get('search')

        if category:
            queryset = queryset.filter(category__slug=category)
        if level:
            queryset = queryset.filter(level=level)
        if is_free:
            queryset = queryset.filter(is_free=is_free.lower() == 'true')
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.order_by('-created_at')


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class CourseEnrollView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        course = get_object_or_404(Course, slug=slug, is_published=True)

        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response({'error': 'Siz allaqachon yozilgansiz'}, status=status.HTTP_400_BAD_REQUEST)

        if not course.is_free:
            return Response({'error': 'Bu pullik kurs'}, status=status.HTTP_402_PAYMENT_REQUIRED)

        enrollment = Enrollment.objects.create(student=request.user, course=course)

        return Response({
            'message': 'Muvaffaqiyatli yozildingiz',
            'enrollment': EnrollmentSerializer(enrollment).data
        }, status=status.HTTP_201_CREATED)


# ENROLLMENT API
class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user).order_by('-enrolled_at')


# LESSON API
class LessonDetailView(generics.RetrieveAPIView):
    serializer_class = LessonDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        lesson = get_object_or_404(Lesson, pk=self.kwargs['pk'])

        if not lesson.is_free:
            enrolled = Enrollment.objects.filter(
                student=self.request.user,
                course=lesson.course
            ).exists()
            if not enrolled:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Bu darsni korish uchun kursga yoziling')

        return lesson


class LessonCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)

        progress, created = LessonProgress.objects.get_or_create(
            student=request.user,
            lesson=lesson,
            defaults={'completed': True, 'completed_at': timezone.now()}
        )

        if not progress.completed:
            progress.completed = True
            progress.completed_at = timezone.now()
            progress.save()

        xp_profile, _ = UserXP.objects.get_or_create(user=request.user)
        if created:
            xp_profile.add_xp(lesson.xp_reward, f'Dars tugatildi: {lesson.title}')

        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=lesson.course
        ).first()

        if enrollment:
            total_lessons = lesson.course.lessons.count()
            completed_lessons = LessonProgress.objects.filter(
                student=request.user,
                lesson__course=lesson.course,
                completed=True
            ).count()

            if total_lessons > 0:
                enrollment.progress = int((completed_lessons / total_lessons) * 100)
                if enrollment.progress >= 100:
                    enrollment.completed = True
                    enrollment.completed_at = timezone.now()
                enrollment.save()

        return Response({
            'message': 'Dars tugatildi',
            'xp_earned': lesson.xp_reward if created else 0,
            'progress': enrollment.progress if enrollment else 0
        })


# QUIZ API
class QuizDetailView(generics.RetrieveAPIView):
    queryset = Quiz.objects.filter(is_active=True)
    serializer_class = QuizDetailSerializer
    permission_classes = [IsAuthenticated]


class QuizStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)

        attempts_count = QuizAttempt.objects.filter(
            quiz=quiz,
            student=request.user
        ).count()

        if attempts_count >= quiz.max_attempts:
            return Response(
                {'error': 'Maksimal urinishlar soni tugadi'},
                status=status.HTTP_400_BAD_REQUEST
            )

        attempt = QuizAttempt.objects.create(quiz=quiz, student=request.user)

        return Response({
            'attempt_id': attempt.id,
            'quiz': QuizDetailSerializer(quiz).data,
            'remaining_attempts': quiz.max_attempts - attempts_count - 1
        })


class QuizSubmitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(
            QuizAttempt,
            pk=attempt_id,
            student=request.user
        )

        if attempt.completed_at:
            return Response(
                {'error': 'Bu urinish allaqachon yakunlangan'},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_points = 0
        earned_points = 0
        correct = 0
        questions = attempt.quiz.questions.all()
        for question in questions:
            total_points += question.points
            response = attempt.responses.filter(question=question).first()
            if not response:
                continue
            selected_ids = {x for x in response.selected_answers.split(',') if x}
            correct_ids = set(str(a.id) for a in question.answers.filter(is_correct=True))
            if selected_ids == correct_ids:
                correct += 1
                earned_points += question.points

        score = int((earned_points / total_points) * 100) if total_points > 0 else 0
        passed = score >= attempt.quiz.passing_score

        attempt.completed_at = timezone.now()
        attempt.score = score
        attempt.passed = passed
        attempt.correct_answers = correct
        attempt.wrong_answers = max(0, questions.count() - correct)
        attempt.save()

        return Response({
            'message': 'Quiz yakunlandi',
            'result': QuizAttemptSerializer(attempt).data
        })


class MyQuizAttemptsView(generics.ListAPIView):
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QuizAttempt.objects.filter(student=self.request.user).order_by('-started_at')


# CERTIFICATE API
class MyCertificatesView(generics.ListAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(student=self.request.user)


class CertificateVerifyView(generics.RetrieveAPIView):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'


# REVIEW API
class CourseReviewsView(generics.ListAPIView):
    serializer_class = CourseReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_slug = self.kwargs['slug']
        return CourseReview.objects.filter(
            course__slug=course_slug,
            is_approved=True
        ).order_by('-created_at')


class ReviewCreateView(generics.CreateAPIView):
    serializer_class = ReviewCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        course = get_object_or_404(Course, slug=self.kwargs['slug'])

        if not Enrollment.objects.filter(student=self.request.user, course=course).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Sharh qoldirish uchun kursga yoziling')

        serializer.save(user=self.request.user, course=course)


# USER PROFILE API
class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        enrollments = Enrollment.objects.filter(student=user)
        certificates = Certificate.objects.filter(student=user)

        try:
            xp_profile = user.xp_profile
            xp_data = UserXPSerializer(xp_profile).data
        except:
            xp_data = {'total_xp': 0, 'level': 1, 'current_streak': 0, 'longest_streak': 0}

        return Response({
            'total_courses': enrollments.count(),
            'completed_courses': enrollments.filter(completed=True).count(),
            'in_progress_courses': enrollments.filter(completed=False).count(),
            'certificates': certificates.count(),
            'xp': xp_data
        })


# LEADERBOARD API
class LeaderboardView(generics.ListAPIView):
    serializer_class = UserXPSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return UserXP.objects.order_by('-total_xp')[:20]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []

        for i, xp_profile in enumerate(queryset, 1):
            data.append({
                'rank': i,
                'user': xp_profile.user.get_full_name() or xp_profile.user.username,
                'level': xp_profile.level,
                'total_xp': xp_profile.total_xp,
                'streak': xp_profile.current_streak
            })

        return Response(data)


# SEARCH API
class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')

        if len(query) < 2:
            return Response({'error': 'Kamida 2 ta belgi kiriting'}, status=400)

        courses = Course.objects.filter(
            is_published=True,
            title__icontains=query
        )[:10]

        return Response({
            'query': query,
            'results': CourseListSerializer(courses, many=True).data,
            'count': courses.count()
        })
