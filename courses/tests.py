import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import AIGradeRecommendation, Assignment, Category, Course, Lesson, Submission
from .views import (
    _extract_file_for_ai,
    analyze_submission_with_ai,
)


def _build_minimal_docx(text):
    buffer = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>',
        )
        archive.writestr(
            'word/document.xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>',
        )
    buffer.seek(0)
    return buffer.read()


def _build_minimal_xlsx():
    buffer = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '</Types>',
        )
        archive.writestr(
            'xl/sharedStrings.xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="2" uniqueCount="2">'
            '<si><t>Mezon</t></si><si><t>To\'g\'ri javob</t></si></sst>',
        )
        archive.writestr(
            'xl/worksheets/sheet1.xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row></sheetData>'
            '</worksheet>',
        )
    buffer.seek(0)
    return buffer.read()


def _build_minimal_pptx(text):
    buffer = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/slides/slide1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            '</Types>',
        )
        archive.writestr(
            'ppt/slides/slide1.xml',
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p>'
            '</p:txBody></p:sp></p:spTree></p:cSld></p:sld>',
        )
    buffer.seek(0)
    return buffer.read()


MEDIA_ROOT = Path(__file__).resolve().parent.parent / 'test_media'


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class AITeacherFlowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.makedirs(MEDIA_ROOT, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

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

    def test_extract_file_for_ai_reads_docx_xlsx_pptx(self):
        docx = SimpleUploadedFile(
            'task.docx',
            _build_minimal_docx('Word vazifa matni'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        xlsx = SimpleUploadedFile(
            'rubric.xlsx',
            _build_minimal_xlsx(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        pptx = SimpleUploadedFile(
            'slides.pptx',
            _build_minimal_pptx('Slide vazifa matni'),
            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

        assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='Files assignment',
            description='desc',
            instructions='instr',
            max_score=100,
        )
        assignment.attachment.save('task.docx', docx)
        submission = Submission.objects.create(
            student=self.student,
            assignment=assignment,
            content='',
        )
        submission.file.save('sheet.xlsx', xlsx)

        teacher_data = _extract_file_for_ai(assignment.attachment, "O'qituvchi vazifa")
        student_data = _extract_file_for_ai(submission.file, "Talaba javobi")

        self.assertIn('Word vazifa matni', teacher_data['text'])
        self.assertIn('Mezon', student_data['text'])

        ppt_assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='PPT assignment',
            description='desc',
            instructions='instr',
            max_score=100,
        )
        ppt_assignment.attachment.save('slides.pptx', pptx)
        ppt_data = _extract_file_for_ai(ppt_assignment.attachment, "O'qituvchi vazifa")
        self.assertIn('Slide vazifa matni', ppt_data['text'])

    @patch('courses.views._call_gemini')
    def test_ai_prompt_includes_teacher_and_student_file_context(self, mock_call):
        mock_call.return_value = {
            'ok': True,
            'text': '{"score": 88, "confidence": 0.9, "analysis": "Mos", "strengths": "-", "weaknesses": "-", "suggestions": "-"}',
        }
        assignment_file = SimpleUploadedFile(
            'task.docx',
            _build_minimal_docx('Teacher requirement content'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        student_file = SimpleUploadedFile(
            'answer.pptx',
            _build_minimal_pptx('Student answer content'),
            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

        assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='Compare files',
            description='Asosiy vazifa',
            instructions='Talaba mos javob bersin',
            max_score=90,
        )
        assignment.attachment.save('task.docx', assignment_file)

        submission = Submission.objects.create(
            student=self.student,
            assignment=assignment,
            content='Talaba matn javobi',
        )
        submission.file.save('answer.pptx', student_file)

        result = analyze_submission_with_ai(submission, assignment)

        self.assertEqual(result['score'], 88)
        sent_prompt = mock_call.call_args.args[0][0]['text']
        self.assertIn("O'qituvchi vazifa fayli", sent_prompt)
        self.assertIn("Talaba javobi fayli", sent_prompt)
        self.assertIn('Teacher requirement content', sent_prompt)
        self.assertIn('Student answer content', sent_prompt)


class CoursePublishingFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username='teacher_courses', password='testpass123')
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.save(update_fields=['is_teacher'])
        cls.category = Category.objects.create(name='Course Tests', slug='course-tests')

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.teacher)

    def test_teacher_course_create_defaults_to_published(self):
        response = self.client.get(reverse('teacher_course_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].initial.get('is_published'))

    def test_teacher_gets_warning_when_saving_draft_course(self):
        response = self.client.post(
            reverse('teacher_course_create'),
            {
                'title': 'Draft course',
                'description': 'desc',
                'short_description': '',
                'category': self.category.pk,
                'level': 'beginner',
                'language': "O'zbek",
                'price': 0,
                'discount_price': '',
                'requirements': '',
                'what_you_learn': '',
                'is_free': 'on',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in response.context['messages']]
        self.assertTrue(any('qoralama holatda saqlandi' in message for message in messages))

    def test_teacher_gets_success_when_saving_published_course(self):
        response = self.client.post(
            reverse('teacher_course_create'),
            {
                'title': 'Published course',
                'description': 'desc',
                'short_description': '',
                'category': self.category.pk,
                'level': 'beginner',
                'language': "O'zbek",
                'price': 0,
                'discount_price': '',
                'requirements': '',
                'what_you_learn': '',
                'is_free': 'on',
                'is_published': 'on',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        messages = [str(message) for message in response.context['messages']]
        self.assertTrue(any('talabalar uchun nashr qilindi' in message for message in messages))
