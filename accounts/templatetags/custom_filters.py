from django import template
from django.contrib.auth.models import AnonymousUser

register = template.Library()

@register.simple_tag
def get_unread_notifications_count(user):
    if user.is_authenticated:
        return user.user_notifications.filter(is_read=False).count()
    return 0