web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py ensure_superuser && gunicorn lms_project.wsgi --bind 0.0.0.0:$PORT
