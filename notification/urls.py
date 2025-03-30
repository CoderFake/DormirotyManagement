from django.urls import path
from . import views

app_name = 'notification'

urlpatterns = [
    # Thông báo cho người dùng
    path('list/', views.notification_list_view, name='list'),
    path('detail/<uuid:notification_id>/', views.notification_detail_view, name='detail'),
    path('mark-as-read/<uuid:notification_id>/', views.mark_as_read_view, name='mark_as_read'),
    path('mark-all-as-read/', views.mark_all_as_read_view, name='mark_all_as_read'),

    # Thông báo chung
    path('announcements/', views.announcement_list_view, name='announcement_list'),
    path('announcement/<uuid:announcement_id>/', views.announcement_detail_view, name='announcement_detail'),

    # Quản lý thông báo (Admin)
    path('category/list/', views.category_list_view, name='category_list'),
    path('category/create/', views.category_create_view, name='category_create'),
    path('category/<uuid:category_id>/edit/', views.category_edit_view, name='category_edit'),
    path('category/<uuid:category_id>/delete/', views.category_delete_view, name='category_delete'),

    path('create/', views.notification_create_view, name='create'),
    path('edit/<uuid:notification_id>/', views.notification_edit_view, name='edit'),
    path('delete/<uuid:notification_id>/', views.notification_delete_view, name='delete'),

    path('announcement/create/', views.announcement_create_view, name='announcement_create'),
    path('announcement/<uuid:announcement_id>/edit/', views.announcement_edit_view, name='announcement_edit'),
    path('announcement/<uuid:announcement_id>/delete/', views.announcement_delete_view, name='announcement_delete'),

    # API
    path('api/unread-count/', views.unread_count_api, name='unread_count_api'),
    path('api/update-notifications/', views.update_notifications_api, name='update_notifications_api'),
]
