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

from .models import AIGradeRecommendation, Assignment, Attendance, Category, Course, Lesson, Notification, Submission
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


def _build_zip_with_supported_files():
    buffer = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('src/main.py', 'def solve():\n    return "zip works"\n')
        archive.writestr('notes/readme.txt', 'ZIP matnli izoh')
        archive.writestr('docs/task.docx', _build_minimal_docx('ZIP ichidagi Word matni'))
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
        cls.supervisor = User.objects.create_user(username='supervisor_ai', password='testpass123')
        cls.supervisor.profile.is_supervisor = True
        cls.supervisor.profile.save(update_fields=['is_supervisor'])
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

    def test_supervisor_dashboard_requires_supervisor_role(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(reverse('supervisor_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nazoratchi Paneli')

    def test_supervisor_can_approve_teacher_score(self):
        recommendation = AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=68,
            max_score=100,
            confidence=0.8,
            analysis='Review needed',
            teacher_score=72,
            teacher_feedback='Teacher feedback',
            is_reviewed=True,
        )
        self.client.force_login(self.supervisor)

        response = self.client.post(
            reverse('supervisor_recommendation_detail', args=[recommendation.pk]),
            {'action': 'approve', 'supervisor_comment': 'Mos keladi.'},
            follow=True,
        )

        recommendation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommendation.supervisor_status,
            AIGradeRecommendation.SUPERVISOR_STATUS_APPROVED,
        )
        self.assertEqual(recommendation.supervisor_score, 72)
        self.assertEqual(recommendation.supervisor_reviewer, self.supervisor)

    def test_supervisor_can_request_regrade(self):
        recommendation = AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=50,
            max_score=100,
            confidence=0.5,
            analysis='Mismatch',
            teacher_score=90,
            teacher_feedback='Teacher feedback',
            is_reviewed=True,
        )
        self.client.force_login(self.supervisor)

        response = self.client.post(
            reverse('supervisor_recommendation_detail', args=[recommendation.pk]),
            {'action': 'request_review', 'supervisor_comment': 'Farq juda katta.'},
            follow=True,
        )

        recommendation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommendation.supervisor_status,
            AIGradeRecommendation.SUPERVISOR_STATUS_NEEDS_REVIEW,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.teacher,
                title="Supervisor qayta ko'rib chiqishni so'radi",
            ).exists()
        )

    def test_supervisor_can_override_final_score(self):
        recommendation = AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=78,
            max_score=100,
            confidence=0.8,
            analysis='Needs override',
            teacher_score=90,
            teacher_feedback='Teacher feedback',
            is_reviewed=True,
        )
        self.submission.score = 90
        self.submission.feedback = 'Teacher feedback'
        self.submission.is_graded = True
        self.submission.save(update_fields=['score', 'feedback', 'is_graded'])
        self.client.force_login(self.supervisor)

        response = self.client.post(
            reverse('supervisor_recommendation_detail', args=[recommendation.pk]),
            {
                'action': 'override',
                'override_score': '81',
                'supervisor_comment': 'Final score corrected.',
            },
            follow=True,
        )

        recommendation.refresh_from_db()
        self.submission.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommendation.supervisor_status,
            AIGradeRecommendation.SUPERVISOR_STATUS_OVERRIDDEN,
        )
        self.assertEqual(recommendation.supervisor_score, 81)
        self.assertEqual(self.submission.score, 81)
        self.assertIn('Supervisor izohi', self.submission.feedback)

    def test_teacher_regrade_resets_supervisor_decision(self):
        recommendation = AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=65,
            max_score=100,
            confidence=0.7,
            analysis='Reset test',
            teacher_score=70,
            teacher_feedback='Old teacher feedback',
            is_reviewed=True,
            supervisor_status=AIGradeRecommendation.SUPERVISOR_STATUS_APPROVED,
            supervisor_comment='Approved before',
            supervisor_score=70,
            supervisor_reviewer=self.supervisor,
        )
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('teacher_grade_submission', args=[self.submission.pk]),
            {'score': '74', 'feedback': 'Updated teacher feedback'},
            follow=True,
        )

        recommendation.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommendation.supervisor_status,
            AIGradeRecommendation.SUPERVISOR_STATUS_PENDING,
        )
        self.assertIsNone(recommendation.supervisor_score)
        self.assertEqual(recommendation.supervisor_comment, '')
        self.assertIsNone(recommendation.supervisor_reviewer)

    def test_difference_level_uses_score_percentage_per_submission(self):
        small_scale = AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=80,
            max_score=100,
            confidence=0.7,
            analysis='A',
            teacher_score=68,
            is_reviewed=True,
            score_difference=12,
        )

        second_assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='Large scale assignment',
            description='desc',
            instructions='instr',
            max_score=200,
        )
        second_submission = Submission.objects.create(
            student=self.student,
            assignment=second_assignment,
            content='response',
        )
        large_scale = AIGradeRecommendation.objects.create(
            submission=second_submission,
            ai_score=160,
            max_score=200,
            confidence=0.7,
            analysis='B',
            teacher_score=148,
            is_reviewed=True,
            score_difference=12,
        )

        self.assertEqual(small_scale.difference_level, AIGradeRecommendation.DIFFERENCE_LEVEL_MEDIUM)
        self.assertEqual(large_scale.difference_level, AIGradeRecommendation.DIFFERENCE_LEVEL_SMALL)
        self.assertEqual(small_scale.difference_percent, 12.0)
        self.assertEqual(large_scale.difference_percent, 6.0)

    def test_student_assignment_detail_hides_ai_recommendation(self):
        AIGradeRecommendation.objects.create(
            submission=self.submission,
            ai_score=75,
            max_score=100,
            confidence=0.6,
            analysis='Internal AI analysis',
            strengths='Strong points',
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('assignment_detail', args=[self.assignment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'AI tavsiya tahlili')
        self.assertNotContains(response, 'Internal AI analysis')

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

    def test_extract_file_for_ai_reads_supported_files_from_zip(self):
        zip_file = SimpleUploadedFile(
            'submission.zip',
            _build_zip_with_supported_files(),
            content_type='application/zip',
        )
        zip_assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='ZIP assignment',
            description='ZIP desc',
            instructions='ZIP instr',
            max_score=100,
        )

        submission = Submission.objects.create(
            student=self.student,
            assignment=zip_assignment,
            content='',
        )
        submission.file.save('submission.zip', zip_file)

        extracted = _extract_file_for_ai(submission.file, "Talaba javobi")

        self.assertIn('zip works', extracted['text'])
        self.assertIn('ZIP matnli izoh', extracted['text'])
        self.assertIn('ZIP ichidagi Word matni', extracted['text'])
        self.assertTrue(any('ZIP fayli tahlil qilindi' in note for note in extracted['notes']))

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

    @patch('courses.views._call_gemini')
    def test_ai_prompt_includes_zip_contents(self, mock_call):
        mock_call.return_value = {
            'ok': True,
            'text': '{"score": 77, "confidence": 0.8, "analysis": "ZIP mos", "strengths": "-", "weaknesses": "-", "suggestions": "-"}',
        }
        student_zip = SimpleUploadedFile(
            'answer.zip',
            _build_zip_with_supported_files(),
            content_type='application/zip',
        )
        zip_assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='ZIP prompt assignment',
            description='ZIP prompt desc',
            instructions='ZIP prompt instr',
            max_score=100,
        )

        submission = Submission.objects.create(
            student=self.student,
            assignment=zip_assignment,
            content='ZIP submission',
        )
        submission.file.save('answer.zip', student_zip)

        result = analyze_submission_with_ai(submission, zip_assignment)

        self.assertEqual(result['score'], 77)
        sent_prompt = mock_call.call_args.args[0][0]['text']
        self.assertIn('src/main.py', sent_prompt)
        self.assertIn('zip works', sent_prompt)
        self.assertIn('ZIP ichidagi Word matni', sent_prompt)


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


class AttendanceFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(username='teacher_attendance', password='testpass123')
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.save(update_fields=['is_teacher'])
        cls.student = User.objects.create_user(username='student_attendance', password='testpass123')
        cls.category = Category.objects.create(name='Attendance Category', slug='attendance-category')
        cls.course = Course.objects.create(
            title='Attendance Course',
            description='Course for attendance flow',
            teacher=cls.teacher,
            category=cls.category,
            is_published=True,
            is_free=True,
            price=0,
        )
        cls.enrollment = cls.course.enrollments.create(student=cls.student)

    def setUp(self):
        self.client = Client()

    def test_teacher_can_mark_attendance_for_course_students(self):
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('teacher_course_attendance', args=[self.course.slug]),
            {
                'attendance_date': '2026-04-14',
                f'status_{self.student.id}': Attendance.STATUS_PRESENT,
                f'note_{self.student.id}': 'Vaqtida keldi',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        attendance = Attendance.objects.get(course=self.course, student=self.student, date='2026-04-14')
        self.assertEqual(attendance.status, Attendance.STATUS_PRESENT)
        self.assertEqual(attendance.note, 'Vaqtida keldi')
        self.assertEqual(attendance.marked_by, self.teacher)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                notification_type='attendance',
                title__contains=self.course.title,
            ).exists()
        )

    def test_student_can_view_my_attendance_page(self):
        Attendance.objects.create(
            course=self.course,
            student=self.student,
            date='2026-04-13',
            status=Attendance.STATUS_LATE,
            note='5 daqiqa kechikdi',
            marked_by=self.teacher,
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('my_attendance'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Attendance Course')
        self.assertContains(response, '5 daqiqa kechikdi')
        self.assertContains(response, 'Kechikdi')
