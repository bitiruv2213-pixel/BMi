from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('oauth/', include('allauth.urls')),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('users/<str:username>/', views.public_profile_view, name='public_profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/delete/', views.delete_account_view, name='delete_account'),

    # Password Change (for logged in users)
    path('password/change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/profile/'
    ), name='password_change'),

    path('password/change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),

    # Password Reset (for users who forgot password)
    path('password/reset/', views.password_reset_request_view, name='password_reset'),
    path('password/reset/done/', views.password_reset_done_view, name='password_reset_done'),
    path('password/reset/confirm/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password/reset/complete/', views.password_reset_complete_view, name='password_reset_complete'),

    # Teacher routes are consolidated under courses.urls
]
