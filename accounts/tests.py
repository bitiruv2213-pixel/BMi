from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from courses.models import Category, Course
from .models import PasswordResetCode


class PublicProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = User.objects.create_user(
            username='public_teacher',
            password='testpass123',
            first_name='Ali',
            last_name='Teacher',
        )
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.bio = 'Python mentor'
        cls.teacher.profile.save(update_fields=['is_teacher', 'bio'])

        category = Category.objects.create(name='Public Category', slug='public-category')
        cls.course = Course.objects.create(
            title='Public Python Course',
            description='desc',
            teacher=cls.teacher,
            category=category,
            is_published=True,
            is_free=True,
            price=0,
        )

    def test_public_profile_page_exists(self):
        response = self.client.get(reverse('public_profile', args=[self.teacher.username]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.teacher.username)
        self.assertContains(response, self.course.title)


class PasswordResetFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='reset_user',
            email='reset@example.com',
            password='OldPass123!',
            first_name='Reset',
        )

    @patch('accounts.views._generate_password_reset_code', return_value='123456')
    def test_request_sends_code_to_registered_email(self, mocked_code):
        response = self.client.post(reverse('password_reset'), {'email': self.user.email})

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('123456', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(PasswordResetCode.objects.filter(user=self.user, used_at__isnull=True).count(), 1)

    @patch('accounts.views._generate_password_reset_code', return_value='123456')
    def test_valid_code_resets_password(self, mocked_code):
        self.client.post(reverse('password_reset'), {'email': self.user.email})

        response = self.client.post(reverse('password_reset_confirm'), {
            'email': self.user.email,
            'code': '123456',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'NewStrongPass123!',
        })

        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass123!'))
        self.assertEqual(PasswordResetCode.objects.filter(user=self.user, used_at__isnull=True).count(), 0)

    @patch('accounts.views._generate_password_reset_code', return_value='123456')
    def test_invalid_code_does_not_reset_password(self, mocked_code):
        self.client.post(reverse('password_reset'), {'email': self.user.email})

        response = self.client.post(reverse('password_reset_confirm'), {
            'email': self.user.email,
            'code': '000000',
            'new_password1': 'NewStrongPass123!',
            'new_password2': 'NewStrongPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kod noto&#x27;g&#x27;ri yoki muddati tugagan.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))
