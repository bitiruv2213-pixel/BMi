from django.core.management.base import BaseCommand
from django.utils import timezone
from courses.models import DailyChallenge


class Command(BaseCommand):
    help = 'Kunlik vazifalarni yaratish'

    def handle(self, *args, **options):
        today = timezone.now().date()

        challenges = [
            {'title': '3 ta dars tugatish', 'description': 'Bugun 3 ta darsni yakunlang', 'challenge_type': 'lesson',
             'target_value': 3, 'xp_reward': 50},
            {'title': '1 ta quiz yechish', 'description': 'Bugun 1 ta quizdan o\'ting', 'challenge_type': 'quiz',
             'target_value': 1, 'xp_reward': 30},
            {'title': 'Forumda faollik', 'description': 'Forumda 2 ta javob yozing', 'challenge_type': 'forum',
             'target_value': 2, 'xp_reward': 25},
        ]

        created = 0
        for challenge_data in challenges:
            challenge, is_created = DailyChallenge.objects.get_or_create(
                date=today,
                challenge_type=challenge_data['challenge_type'],
                defaults={**challenge_data, 'date': today}
            )
            if is_created:
                created += 1
                self.stdout.write(f"  ✓ {challenge.title} yaratildi")

        self.stdout.write(self.style.SUCCESS(f'\n{created} ta kunlik vazifa yaratildi!'))
