from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import Profile


def _parse_user_list(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Command(BaseCommand):
    help = "Assign LMS roles using profile flags and staff/superuser fields."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admins",
            default="",
            help="Comma-separated usernames to mark as admin (is_staff + is_superuser).",
        )
        parser.add_argument(
            "--supervisors",
            default="",
            help="Comma-separated usernames to mark as supervisor (profile.is_supervisor).",
        )
        parser.add_argument(
            "--teachers",
            default="",
            help="Comma-separated usernames to mark as teacher (profile.is_teacher).",
        )
        parser.add_argument(
            "--students",
            default="",
            help="Comma-separated usernames to force as student (clear teacher/supervisor flags).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without saving.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        admins = set(_parse_user_list(options["admins"]))
        supervisors = set(_parse_user_list(options["supervisors"]))
        teachers = set(_parse_user_list(options["teachers"]))
        students = set(_parse_user_list(options["students"]))
        dry_run = options["dry_run"]

        targets = admins | supervisors | teachers | students
        if not targets:
            self.stdout.write(self.style.WARNING("No users provided. Nothing to change."))
            return

        existing_users = {u.username: u for u in User.objects.filter(username__in=targets)}
        missing = sorted(targets - set(existing_users.keys()))
        if missing:
            self.stdout.write(self.style.WARNING(f"Missing users: {', '.join(missing)}"))

        changes = []

        def _mark_change(user, field, value):
            current = getattr(user, field)
            if current != value:
                changes.append((user.username, field, current, value))
                setattr(user, field, value)

        @transaction.atomic
        def _apply():
            for username, user in existing_users.items():
                profile, _ = Profile.objects.get_or_create(user=user)

                if username in admins:
                    _mark_change(user, "is_staff", True)
                    _mark_change(user, "is_superuser", True)

                if username in supervisors:
                    if profile.is_supervisor is not True:
                        changes.append((username, "profile.is_supervisor", profile.is_supervisor, True))
                        profile.is_supervisor = True

                if username in teachers:
                    if profile.is_teacher is not True:
                        changes.append((username, "profile.is_teacher", profile.is_teacher, True))
                        profile.is_teacher = True

                if username in students:
                    if profile.is_teacher is not False:
                        changes.append((username, "profile.is_teacher", profile.is_teacher, False))
                        profile.is_teacher = False
                    if profile.is_supervisor is not False:
                        changes.append((username, "profile.is_supervisor", profile.is_supervisor, False))
                        profile.is_supervisor = False

                if not dry_run:
                    user.save()
                    profile.save()

        _apply()

        if not changes:
            self.stdout.write(self.style.SUCCESS("No changes needed."))
            return

        self.stdout.write(self.style.SUCCESS("Planned changes:"))
        for username, field, old, new in changes:
            self.stdout.write(f"  {username}: {field} {old} -> {new}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes saved."))
