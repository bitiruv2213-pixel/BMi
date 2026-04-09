# LMS Platform - AI Coding Agent Guide

## Project Overview
This is a **Django-based Learning Management System (LMS)** with gamification, certificates, payments, and AI chatbot features. The project uses:
- **Framework:** Django 4.2
- **Python:** 3.11+
- **Database:** SQLite (dev), PostgreSQL (production)
- **Key Dependencies:** DRF (Serializers), Pillow (Images), Google Genai (AI), Gunicorn (Production)

## Architecture & Core Modules

### App Structure
- **`accounts/`** - User authentication, profiles, teacher/student roles, `is_supervisor` flag
- **`courses/`** - Core business logic: courses, lessons, quizzes, certificates, gamification
- **`lms_project/`** - Settings, URLs, WSGI/ASGI configuration
- **`media/` & `static/`** - User uploads (avatars, thumbnails) and assets

### Data Flow (Critical Pattern)
1. **User Profile Creation:** Signals auto-create `Profile` on user registration (`accounts/models.py` - `post_save`)
2. **Course Enrollment → Notifications:** Enrollment triggers signal that creates notifications for student & teacher
3. **Gamification Loop:** XP earned → Badge checks → Notifications → Leaderboard updates
4. **Certificates:** Auto-issued when enrollment marked `completed=True`, triggers certificate signal

**See:** `courses/signals.py` - all event-driven updates use `@receiver(post_save, sender=Model)`

## Essential Patterns & Conventions

### Models & Database
- **Slug Fields:** Always auto-generate via `slugify()` in `save()` method (see `Category.save()`)
- **Timestamps:** Use `auto_now_add=True` (created) & `auto_now=True` (updated)
- **Foreign Keys:** Use `select_related()` in QuerySets to avoid N+1 queries
- **Example:** `Enrollment.objects.filter(student=user).select_related('course')`

### Views & QuerySets
- **Dashboard View:** Combine multiple QuerySets with `.annotate(Count/Avg)` for stats
- **Filtering:** Use `Q()` objects for OR conditions: `Q(title__icontains=q) | Q(description__icontains=q)`
- **Pagination:** `Paginator(queryset, per_page=12)` - check `course_list()` view
- **Decorators:** `@login_required` for student views; create custom decorator for teacher-only

### Forms & Validation
- **All forms use `class Meta` with explicit field lists** - see `CourseForm` in `courses/forms.py`
- **Widgets:** Apply `form-control` (Bootstrap) to all inputs for consistency
- **File Uploads:** Specify `upload_to` path (e.g., `'courses/thumbnails/'`)

### Signals & Events
- **Profile Auto-Creation:** `@receiver(post_save, sender=User)` in `accounts/models.py`
- **Notifications on Events:** `enrollment_notification`, `certificate_notification`, `badge_notification` in `courses/signals.py`
- **XP Rewards:** Methods like `UserXP.add_xp(amount, reason)` (check models for full signature)

### API Views
- **Serializers:** Model-specific serializers in `courses/serializers.py` (separate List & Detail)
- **Include computed fields:** `SerializerMethodField` for derived data like `full_name`, `courses_count`

### Management Commands
- **Location:** `courses/management/commands/` (e.g., `create_badges.py`, `create_daily_challenges.py`)
- **Pattern:** Inherit `BaseCommand`, use `.handle()` method
- **Run:** `python manage.py create_badges`

### Template Structure
- **Base:** `templates/base.html` - extends layouts
- **App Templates:** Nested in `templates/<app>/` (e.g., `templates/courses/course_list.html`)
- **Custom Tags:** `video_tags.py` in `templatetags/` for reusable template logic

## Critical Development Workflows

### Running Locally
```bash
# Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Development
python manage.py migrate
python manage.py runserver

# Create test data
python manage.py create_badges
python manage.py create_daily_challenges
```

### Database Migrations
- **Always run after model changes:**
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- **Existing migration issue:** `0002_add_is_supervisor.py` - ensure `Profile.is_supervisor` has default value to avoid NOT NULL constraint errors

### Testing
- Test files exist in `tests.py` per app - follow Django TestCase pattern
- Use `django.test.Client` for view testing

### Production Deployment
- **Server:** Gunicorn via `Procfile` or `nixpacks.toml`
- **Static Files:** `python manage.py collectstatic` (WhiteNoise handles serving)
- **Database:** Use `DATABASE_URL` env var (auto-configured via `dj_database_url`)
- **Environment:** Set `DEBUG=False`, `SECRET_KEY`, and database URL for production

## Known Issues & Workarounds
- **is_supervisor Field Error:** Ensure all existing Profile records have a default value (migration 0002 should set `default=False`)
- **AI Chatbot:** Google Genai integration in `test_gemini.py` - API key from environment (`GENAI_API_KEY`)

## File Reference Map
| Task | File(s) |
|------|---------|
| Add new model | `courses/models.py` |
| Create view | `courses/views.py` |
| Add endpoint | `courses/api_views.py` + `courses/serializers.py` |
| Handle event | `courses/signals.py` (use `@receiver`) |
| Render page | `templates/courses/` |
| User roles | `accounts/models.py` (`is_teacher`, `is_supervisor`) |
| Configuration | `lms_project/settings.py` (INSTALLED_APPS, DATABASES, etc.) |
| Gamification | `courses/models.py` - Badge, UserXP, DailyChallenge |

## Code Style & Best Practices
- **Query Optimization:** Always use `select_related()` for ForeignKey, `prefetch_related()` for reverse relations
- **Transactions:** Use `@transaction.atomic` for critical workflows (payments, certificate issuance)
- **Logging:** Use `import logging; logger = logging.getLogger(__name__)`
- **Comments:** Markdown headers (`# ========`) section code in models.py/views.py
- **Error Handling:** Check `error.txt` for past integration issues (NOT NULL constraints)

---
*Last updated: January 2026. LMS1 Repository.*
