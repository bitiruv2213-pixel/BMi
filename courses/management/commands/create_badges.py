from django.core.management.base import BaseCommand
from courses.models import Badge


class Command(BaseCommand):
    help = 'Standart badgelarni yaratish'

    def handle(self, *args, **options):
        badges = [
            # Kurs badgelari
            {'name': 'Birinchi qadam', 'description': 'Birinchi kursni tugatdingiz!',
             'icon': 'bi-flag', 'color': '#10b981', 'badge_type': 'course', 'requirement_value': 1, 'xp_reward': 100},
            {'name': '5 ta kurs', 'description': '5 ta kursni tugatdingiz!', 'icon': 'bi-book',
             'color': '#3b82f6', 'badge_type': 'course', 'requirement_value': 5, 'xp_reward': 250},
            {'name': '10 ta kurs', 'description': '10 ta kursni tugatdingiz!',
             'icon': 'bi-books', 'color': '#8b5cf6', 'badge_type': 'course', 'requirement_value': 10, 'xp_reward': 500},
            {'name': 'Kurs ustasi', 'description': '25 ta kursni tugatdingiz!',
             'icon': 'bi-mortarboard', 'color': '#f59e0b', 'badge_type': 'course', 'requirement_value': 25, 'xp_reward': 1000},

            # Quiz badgelari
            {'name': 'Birinchi quiz', 'description': 'Birinchi quizdan o\'tdingiz!',
             'icon': 'bi-patch-check', 'color': '#10b981', 'badge_type': 'xp', 'requirement_value': 1, 'xp_reward': 50},
            {'name': 'Quiz Pro', 'description': '10 ta quizdan o\'tdingiz!',
             'icon': 'bi-check-circle', 'color': '#3b82f6', 'badge_type': 'xp', 'requirement_value': 10, 'xp_reward': 200},
            {'name': 'Quiz Master', 'description': '50 ta quizdan o\'tdingiz!',
             'icon': 'bi-trophy', 'color': '#f59e0b', 'badge_type': 'xp', 'requirement_value': 50, 'xp_reward': 500},

            # Streak badgelari
            {'name': 'Haftalik streak', 'description': '7 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#ef4444', 'badge_type': 'streak', 'requirement_value': 7, 'xp_reward': 100},
            {'name': 'Oylik streak', 'description': '30 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#f97316', 'badge_type': 'streak', 'requirement_value': 30, 'xp_reward': 500},
            {'name': '100 kunlik streak', 'description': '100 kun ketma-ket o\'qidingiz!',
             'icon': 'bi-fire', 'color': '#dc2626', 'badge_type': 'streak', 'requirement_value': 100, 'xp_reward': 2000},

            # Daraja badgelari
            {'name': 'Daraja 5', 'description': '5-darajaga yetdingiz!', 'icon': 'bi-star',
             'color': '#6366f1', 'badge_type': 'special', 'requirement_value': 5, 'xp_reward': 100},
            {'name': 'Daraja 10', 'description': '10-darajaga yetdingiz!', 'icon': 'bi-star-fill',
             'color': '#8b5cf6', 'badge_type': 'special', 'requirement_value': 10, 'xp_reward': 300},
            {'name': 'Daraja 25', 'description': '25-darajaga yetdingiz!', 'icon': 'bi-stars',
             'color': '#f59e0b', 'badge_type': 'special', 'requirement_value': 25, 'xp_reward': 1000},

            # Ijtimoiy badgelar
            {'name': 'Yordamchi', 'description': 'Forumda 10 ta yechim belgilandi!',
             'icon': 'bi-hand-thumbs-up', 'color': '#10b981', 'badge_type': 'social', 'requirement_value': 10,
             'xp_reward': 200},
            {'name': 'Faol ishtirokchi', 'description': 'Forumda 50 ta javob yozdingiz!',
             'icon': 'bi-chat-dots', 'color': '#3b82f6', 'badge_type': 'social', 'requirement_value': 50, 'xp_reward': 300},
        ]

        created = 0
        for badge_data in badges:
            badge, is_created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if is_created:
                created += 1
                self.stdout.write(f"  ✓ {badge.name} yaratildi")

        self.stdout.write(self.style.SUCCESS(f'\n{created} ta badge yaratildi!'))
