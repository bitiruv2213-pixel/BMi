from django.urls import path
from . import views

urlpatterns = [
    # Home & Dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Courses
    path('courses/', views.course_list, name='course_list'),
    path('courses/<slug:slug>/', views.course_detail, name='course_detail'),
    path('courses/<slug:slug>/enroll/', views.enroll_course, name='enroll_course'),
    path('courses/<slug:slug>/learn/', views.course_learn, name='course_learn'),
    path('courses/<slug:slug>/review/', views.review_create, name='review_create'),
    path('courses/<slug:slug>/reviews/', views.review_list, name='review_list'),

    # My Courses
    path('my-courses/', views.my_courses, name='my_courses'),

    # Lessons
    path('courses/<slug:course_slug>/lessons/<int:lesson_id>/complete/', views.mark_lesson_complete,
         name='mark_lesson_complete'),

    # Quiz
    path('quiz/<int:pk>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:pk>/take/', views.quiz_take, name='quiz_take'),
    path('quiz/<int:pk>/statistics/', views.quiz_statistics, name='quiz_statistics'),
    path('quiz/result/<int:pk>/', views.quiz_result, name='quiz_result'),

    # Assignment
    path('assignment/<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('assignment/<int:pk>/submit/', views.assignment_submit, name='assignment_submit'),

    # Certificate
    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificates/<uuid:pk>/', views.certificate_detail, name='certificate_detail'),
    path('certificates/<uuid:pk>/download/', views.certificate_download, name='certificate_download'),
    path('certificates/verify/<str:certificate_number>/', views.certificate_verify, name='certificate_verify'),

    # Discussion
    path('courses/<slug:slug>/discussions/', views.discussion_list, name='discussion_list'),
    path('courses/<slug:slug>/discussions/create/', views.discussion_create, name='discussion_create'),
    path('discussions/<int:pk>/', views.discussion_detail, name='discussion_detail'),
    path('reply/<int:pk>/delete/', views.reply_delete, name='reply_delete'),

    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/recent/', views.notification_recent, name='notification_recent'),

    # Payment
    path('courses/<slug:slug>/checkout/', views.payment_checkout, name='payment_checkout'),
    path('courses/<slug:slug>/payment/process/', views.payment_process, name='payment_process'),
    path('courses/<slug:slug>/payment/success/', views.payment_success, name='payment_success'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/<slug:slug>/toggle/', views.wishlist_toggle, name='wishlist_toggle'),

    # Teacher Panel
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/courses/create/', views.teacher_course_create, name='teacher_course_create'),
    path('teacher/courses/<slug:slug>/edit/', views.teacher_course_edit, name='teacher_course_edit'),
    path('teacher/courses/<slug:slug>/students/', views.teacher_course_students, name='teacher_course_students'),
    path('teacher/courses/<slug:course_slug>/student/<int:user_id>/', views.teacher_student_detail,
         name='teacher_student_detail'),
    path('teacher/courses/<slug:slug>/delete/', views.teacher_course_delete, name='teacher_course_delete'),
    path('teacher/courses/<slug:course_slug>/lessons/create/', views.teacher_lesson_create,
         name='teacher_lesson_create'),
    path('teacher/lessons/<int:pk>/edit/', views.teacher_lesson_edit, name='teacher_lesson_edit'),
    path('teacher/lessons/<int:pk>/delete/', views.teacher_lesson_delete, name='teacher_lesson_delete'),
    path('teacher/statistics/', views.teacher_statistics, name='teacher_statistics'),

    # Teacher - AI Grading
    path('teacher/courses/<slug:slug>/submissions/', views.teacher_submissions, name='teacher_submissions'),
    path('teacher/submission/<int:pk>/grade/', views.teacher_grade_submission, name='teacher_grade_submission'),

    # Supervisor Panel
    path('supervisor/dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('supervisor/recommendation/<int:pk>/', views.supervisor_recommendation_detail,
         name='supervisor_recommendation_detail'),

    # Gamification
    path('gamification/', views.gamification_profile, name='gamification_profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('challenges/', views.daily_challenges, name='daily_challenges'),

    # Chatbot
    path('chatbot/', views.chatbot_view, name='chatbot_view'),
    path('chatbot/send/', views.chatbot_send, name='chatbot_send'),
    path('chatbot/history/', views.chatbot_history, name='chatbot_history'),
    path('chatbot/clear/', views.chatbot_clear, name='chatbot_clear'),
    path('chatbot/course/<slug:slug>/', views.chatbot_view, name='chatbot_course'),

    # Code Editor
    path('code-editor/', views.code_editor, name='code_editor'),
    path('code-editor/execute/', views.code_execute, name='code_execute'),

    # Statistics
    path('statistics/', views.student_statistics, name='student_statistics'),

    # Game Arena
    path('game-arena/', views.game_arena, name='game_arena'),
    path('game-arena/typing/', views.typing_game, name='typing_game'),
    path('game-arena/typing/submit/', views.typing_game_submit, name='typing_game_submit'),
    path('game-arena/code/', views.code_challenge_list, name='code_challenge_list'),
    path('game-arena/code/<int:pk>/', views.code_challenge_play, name='code_challenge_play'),
    path('game-arena/code/run/', views.code_challenge_run, name='code_challenge_run'),
    path('game-arena/code/submit/', views.code_challenge_submit, name='code_challenge_submit'),
    path('game-arena/math/', views.math_game, name='math_game'),
    path('game-arena/math/submit/', views.math_game_submit, name='math_game_submit'),
    path('game-arena/memory/', views.memory_game, name='memory_game'),
    path('game-arena/memory/submit/', views.memory_game_submit, name='memory_game_submit'),
    path('game-arena/leaderboard/<str:game_type>/', views.game_leaderboard, name='game_leaderboard'),
]
