from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import AIGradeRecommendation, Assignment, Category, Course, Lesson, Submission
from .views import analyze_submission_with_ai


class AITeacherFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username='teacher_ai', password='testpass123')
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.save(update_fields=['is_teacher'])

        cls.admin = User.objects.create_superuser(
            username='admin_ai',
            email='admin@example.com',
            password='testpass123',
        )
        cls.student = User.objects.create_user(username='student_ai', password='testpass123')

        cls.category = Category.objects.create(name='Tests', slug='tests')
        cls.course = Course.objects.create(
            title='AI Flow Course',
            description='Course for AI flow tests',
            teacher=cls.teacher,
            category=cls.category,
            is_published=True,
            is_free=True,
            price=0,
        )
        cls.lesson = Lesson.objects.create(
            course=cls.course,
            title='AI Lesson',
            lesson_type='assignment',
            content='Lesson content',
            order=1,
            is_published=True,
        )
        cls.assignment = Assignment.objects.create(
            lesson=cls.lesson,
            title='AI Assignment',
            description='Write a Python function',
            instructions='Explain your approach',
            max_score=100,
        )
        cls.submission = Submission.objects.create(
            student=cls.student,
            assignment=cls.assignment,
            content='def add(a, b):\n    return a + b',
        )

    def setUp(self):
        self.client = Client()

    def test_student_cannot_open_ai_mentor(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('chatbot_view'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('dashboard'))

    @patch('courses.views._call_gemini')
    def test_teacher_chatbot_returns_fallback_payload_when_ai_unavailable(self, mock_call):
        mock_call.return_value = {
            'ok': False,
            'error_type': 'network',
            'message': 'blocked',
        }
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('chatbot_send'),
            {'message': 'Django urls.py nima qiladi?'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertIn('Django bo', payload['response'])

    @patch('courses.views._call_gemini')
    def test_ai_grading_clamps_invalid_model_output(self, mock_call):
        mock_call.return_value = {
            'ok': True,
            'text': '{"score": 1000, "confidence": 5, "analysis": "ok"}',
        }

        result = analyze_submission_with_ai(self.submission, self.assignment)

        self.assertEqual(result['score'], 100)
        self.assertEqual(result['confidence'], 1.0)
        self.assertEqual(result['analysis'], 'ok')

    def test_teacher_grade_submission_rejects_invalid_score(self):
        AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=70,
            max_score=100,
            confidence=0.8,
            analysis='Test analysis',
        )
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('teacher_grade_submission', args=[self.submission.pk]),
            {'score': 'not-a-number', 'feedback': 'bad input'},
        )

        self.submission.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.submission.is_graded)

    @patch('courses.views._call_gemini')
    def test_teacher_burst_requests_keep_working(self, mock_call):
        mock_call.return_value = {
            'ok': False,
            'error_type': 'network',
            'message': 'blocked',
        }
        self.client.force_login(self.teacher)

        for _ in range(15):
            mentor_response = self.client.post(
                reverse('chatbot_send'),
                {'message': 'Python error nima?'},
            )
            self.assertEqual(mentor_response.status_code, 200)

        AIGradeRecommendation.objects.filter(submission=self.submission).delete()
        for _ in range(10):
            grade_response = self.client.get(
                reverse('teacher_grade_submission', args=[self.submission.pk]) + '?reanalyze=1'
            )
            self.assertEqual(grade_response.status_code, 200)

        self.assertTrue(AIGradeRecommendation.objects.filter(submission=self.submission).exists())

    def test_teacher_submissions_page_loads_with_ai_recommendations(self):
        AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=60,
            max_score=100,
            confidence=0.4,
            analysis='Fallback',
        )
        self.client.force_login(self.teacher)

        response = self.client.get(reverse('teacher_submissions', args=[self.course.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.submission.student.username)
