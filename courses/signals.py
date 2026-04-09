from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Enrollment, Notification, UserXP, Certificate, UserBadge, Badge


@receiver(post_save, sender=Enrollment)
def enrollment_notification(sender, instance, created, **kwargs):
    """Kursga yozilganda notification yuborish"""
    if created:
        # Student uchun notification
        Notification.objects.create(
            recipient=instance.student,
            title="Kursga yozildingiz!",
            message=f"Siz '{instance.course.title}' kursiga muvaffaqiyatli yozildingiz.",
            notification_type='enrollment'
        )

        # Teacher uchun notification
        if instance.course.teacher:
            Notification.objects.create(
                recipient=instance.course.teacher,
                title="Yangi talaba!",
                message=f"{instance.student.get_full_name() or instance.student.username} sizning '{instance.course.title}' kursiga yozildi.",
                notification_type='enrollment'
            )


@receiver(post_save, sender=Certificate)
def certificate_notification(sender, instance, created, **kwargs):
    """Sertifikat olganda notification yuborish"""
    if created:
        Notification.objects.create(
            recipient=instance.student,
            title="Sertifikat oldingiz! 🎉",
            message=f"Tabriklaymiz! Siz '{instance.course.title}' kursini tugatdingiz va sertifikat oldingiz.",
            notification_type='certificate'
        )


@receiver(post_save, sender=UserBadge)
def badge_notification(sender, instance, created, **kwargs):
    """Badge olganda notification yuborish"""
    if created:
        Notification.objects.create(
            recipient=instance.user,
            title="Yangi nishon! 🏆",
            message=f"Tabriklaymiz! Siz '{instance.badge.name}' nishonini qo'lga kiritdingiz.",
            notification_type='badge'
        )

        # Badge uchun XP qo'shish
        if instance.badge.xp_reward > 0:
            xp_profile, _ = UserXP.objects.get_or_create(user=instance.user)
            xp_profile.add_xp(instance.badge.xp_reward, f"'{instance.badge.name}' nishoni uchun")