from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('revenue-report/', views.revenue_report, name='revenue_report'),
    path('revenue-report-detailed/', views.revenue_report_detailed_view, name='revenue_report_detailed'),
    path('occupancy-report/', views.occupancy_report, name='occupancy_report'),
    path('maintenance-report/', views.maintenance_report, name='maintenance_report'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('notification-settings/', views.notification_settings, name='notification_settings'),
]