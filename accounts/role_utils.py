from typing import Optional


def _get_profile(user) -> Optional[object]:
    return getattr(user, 'profile', None)


def is_teacher(user) -> bool:
    profile = _get_profile(user)
    return bool(profile and getattr(profile, 'is_teacher', False))


def is_supervisor(user) -> bool:
    profile = _get_profile(user)
    return bool(profile and getattr(profile, 'is_supervisor', False))


def is_admin(user) -> bool:
    return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False))


def get_role(user) -> str:
    if not getattr(user, 'is_authenticated', False):
        return 'anonymous'
    if getattr(user, 'is_superuser', False):
        return 'admin'
    if is_supervisor(user):
        return 'supervisor'
    if is_teacher(user):
        return 'teacher'
    if getattr(user, 'is_staff', False):
        return 'admin'
    return 'student'
