from django.urls import path
from . import views

app_name = 'registration'

urlpatterns = [
    # Views cho người dùng
    path('rooms/', views.room_list_view, name='room_list'),
    path('rooms/<uuid:room_id>/', views.room_detail_view, name='room_detail'),
    path('apply/', views.apply_view, name='apply'),
    path('apply/<uuid:room_id>/', views.apply_view, name='apply_with_room'),
    path('my-applications/', views.my_applications_view, name='my_applications'),
    path('my-contracts/', views.my_contracts_view, name='my_contracts'),

    path('contract/<uuid:contract_id>/', views.contract_detail_view, name='contract_detail'),
    path('contract/<uuid:contract_id>/sign/', views.contract_sign_view, name='contract_sign'),
    path('application/<uuid:application_id>/cancel/', views.application_cancel_view, name='application_cancel'),

    # Views cho Admin
    path('period/list/', views.period_list_view, name='period_list'),
    path('period/create/', views.period_create_view, name='period_create'),
    path('period/<uuid:period_id>/edit/', views.period_edit_view, name='period_edit'),
    path('period/<uuid:period_id>/delete/', views.period_delete_view, name='period_delete'),

    path('application/list/', views.application_list_view, name='application_list'),
    path('application/<uuid:application_id>/', views.application_detail_view, name='application_detail'),
    path('application/<uuid:application_id>/approve/', views.application_approve_view, name='application_approve'),
    path('application/<uuid:application_id>/reject/', views.application_reject_view, name='application_reject'),

    path('contract/list/', views.contract_list_view, name='contract_list'),
    path('contract/<uuid:contract_id>/approve/', views.contract_approve_view, name='contract_approve'),
    path('contract/<uuid:contract_id>/cancel/', views.contract_cancel_view, name='contract_cancel'),

    path('check-in/list/', views.check_in_list_view, name='check_in_list'),
    path('check-in/create/<uuid:contract_id>/', views.check_in_create_view, name='check_in_create'),
    path('check-in/<uuid:check_in_id>/', views.check_in_detail_view, name='check_in_detail'),

    path('check-out/list/', views.check_out_list_view, name='check_out_list'),
    path('check-out/create/<uuid:contract_id>/', views.check_out_create_view, name='check_out_create'),
    path('check-out/<uuid:check_out_id>/', views.check_out_detail_view, name='check_out_detail'),
]
