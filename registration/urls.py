from django.urls import path
from . import views

app_name = 'registration'

urlpatterns = [
    path('rooms/', views.room_list_view, name='room_list'),
    path('rooms/<uuid:room_id>/', views.room_detail_view, name='room_detail'),
    path('apply/', views.apply_view, name='apply'),
    path('apply/<uuid:room_id>/', views.apply_view, name='apply_with_room'),
]