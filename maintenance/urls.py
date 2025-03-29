from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # Views cho sinh viên
    path('request/create/', views.request_create_view, name='request_create'),
    path('my-requests/', views.my_requests_view, name='my_requests'),
    path('request/<uuid:request_id>/', views.request_detail_view, name='request_detail'),
    path('request/<uuid:request_id>/update/', views.request_update_view, name='request_update'),
    path('request/<uuid:request_id>/cancel/', views.request_cancel_view, name='request_cancel'),

    # Views cho Admin/Staff
    path('category/list/', views.category_list_view, name='category_list'),
    path('category/create/', views.category_create_view, name='category_create'),
    path('category/<uuid:category_id>/edit/', views.category_edit_view, name='category_edit'),
    path('category/<uuid:category_id>/delete/', views.category_delete_view, name='category_delete'),

    path('all-requests/', views.request_list_view, name='request_list'),
    path('request/<uuid:request_id>/assign/', views.request_assign_view, name='request_assign'),
    path('request/<uuid:request_id>/admin-edit/', views.request_admin_edit_view, name='request_admin_edit'),
    path('request/<uuid:request_id>/status-update/', views.request_status_update_view, name='request_status_update'),

    # API
    path('api/handle-request/', views.handle_request_api, name='handle_request_api'),
]