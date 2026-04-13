from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0006_seed_game_data'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='aigraderecommendation',
            name='supervisor_comment',
            field=models.TextField(blank=True, help_text='Supervisor izohi'),
        ),
        migrations.AddField(
            model_name='aigraderecommendation',
            name='supervisor_reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='aigraderecommendation',
            name='supervisor_reviewer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervisor_reviews', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='aigraderecommendation',
            name='supervisor_score',
            field=models.IntegerField(blank=True, help_text='Supervisor tasdiqlagan yakuniy ball', null=True),
        ),
        migrations.AddField(
            model_name='aigraderecommendation',
            name='supervisor_status',
            field=models.CharField(choices=[('pending', 'Kutilmoqda'), ('approved', 'Tasdiqlandi'), ('needs_review', "Qayta ko'rib chiqish"), ('overridden', "Supervisor o'zgartirdi")], default='pending', help_text='Supervisor qarori holati', max_length=20),
        ),
    ]
