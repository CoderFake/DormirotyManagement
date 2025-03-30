from django.urls import path
from . import views

app_name = 'dormitory'

urlpatterns = [
    # Quản lý tòa nhà
    path('buildings/', views.building_list_view, name='building_list'),
    path('buildings/create/', views.building_create_view, name='building_create'),
    path('buildings/<uuid:building_id>/', views.building_detail_view, name='building_detail'),
    path('buildings/<uuid:building_id>/edit/', views.building_edit_view, name='building_edit'),
    path('buildings/<uuid:building_id>/delete/', views.building_delete_view, name='building_delete'),

    # Quản lý loại phòng
    path('room-types/', views.room_type_list_view, name='room_type_list'),
    path('room-types/create/', views.room_type_create_view, name='room_type_create'),
    path('room-types/<uuid:room_type_id>/', views.room_type_detail_view, name='room_type_detail'),
    path('room-types/<uuid:room_type_id>/edit/', views.room_type_edit_view, name='room_type_edit'),
    path('room-types/<uuid:room_type_id>/delete/', views.room_type_delete_view, name='room_type_delete'),

    # Quản lý phòng
    path('rooms/', views.room_list_view, name='room_list'),
    path('rooms/create/', views.room_create_view, name='room_create'),
    path('rooms/bulk-create/', views.bulk_room_create_view, name='bulk_room_create'),
    path('rooms/<uuid:room_id>/', views.room_detail_view, name='room_detail'),
    path('rooms/<uuid:room_id>/edit/', views.room_edit_view, name='room_edit'),
    path('rooms/<uuid:room_id>/delete/', views.room_delete_view, name='room_delete'),

    # Quản lý giường
    path('beds/', views.bed_list_view, name='bed_list'),
    path('beds/create/', views.bed_create_view, name='bed_create'),
    path('beds/bulk-create/', views.bulk_bed_create_view, name='bulk_bed_create'),
    path('beds/<uuid:bed_id>/', views.bed_detail_view, name='bed_detail'),
    path('beds/<uuid:bed_id>/edit/', views.bed_edit_view, name='bed_edit'),
    path('beds/<uuid:bed_id>/delete/', views.bed_delete_view, name='bed_delete'),

    # Quản lý tiện nghi
    path('amenities/', views.amenity_list_view, name='amenity_list'),
    path('amenities/create/', views.amenity_create_view, name='amenity_create'),
    path('amenities/<uuid:amenity_id>/edit/', views.amenity_edit_view, name='amenity_edit'),
    path('amenities/<uuid:amenity_id>/delete/', views.amenity_delete_view, name='amenity_delete'),

    # Quản lý tiện nghi phòng
    path('room-amenities/', views.room_amenity_list_view, name='room_amenity_list'),
    path('room-amenities/create/', views.room_amenity_create_view, name='room_amenity_create'),
    path('room-amenities/<uuid:room_amenity_id>/edit/', views.room_amenity_edit_view, name='room_amenity_edit'),
    path('room-amenities/<uuid:room_amenity_id>/delete/', views.room_amenity_delete_view, name='room_amenity_delete'),

    # Các chức năng cho sinh viên
    path('public/buildings/', views.building_public_list_view, name='building_public_list'),
    path('public/buildings/<uuid:building_id>/', views.building_public_detail_view, name='building_public_detail'),
    path('public/room-types/', views.room_type_public_list_view, name='room_type_public_list'),
    path('public/room-types/<uuid:room_type_id>/', views.room_type_public_detail_view, name='room_type_public_detail'),
    path('public/rooms/', views.room_public_list_view, name='room_public_list'),
    path('public/rooms/<uuid:room_id>/', views.room_public_detail_view, name='room_public_detail'),

    # API
    path('api/get-beds/', views.api_get_beds, name='api_get_beds'),
    path('api/get-rooms/', views.api_get_rooms, name='api_get_rooms'),
]