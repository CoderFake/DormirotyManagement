#!/bin/bash

# Đợi cho MySQL khởi động
echo "Đang đợi MySQL khởi động..."
while ! nc -z db 3306; do
  sleep 1
done
echo "MySQL đã sẵn sàng!"

# Thực hiện migrations
echo "Đang áp dụng migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Đang thu thập static files..."
python manage.py collectstatic --noinput

# Tạo hoặc cập nhật Django Site
python manage.py shell -c "
from django.contrib.sites.models import Site
try:
    site = Site.objects.get(id=1)
    site.domain = '${SITE_URL}'
    site.name = 'Hệ thống Quản lý Ký túc xá'
    site.save()
    print('Đã cập nhật thông tin Site')
except Site.DoesNotExist:
    Site.objects.create(
        id=1,
        domain='localhost:8000',
        name='Hệ thống Quản lý Ký túc xá'
    )
    print('Đã tạo mới Site')
"

python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(email='${SUPERUSER_EMAIL}').exists():
    User.objects.create_superuser(
        email='${SUPERUSER_EMAIL}',
        password='${SUPERUSER_PASS}',
        full_name='${SUPERUSER_NAME}',
        user_type='admin'
    )
    print('Superuser đã được tạo')
else:
    print('Superuser đã tồn tại')
"

echo "Khởi động application server..."
exec gunicorn DormitoryManagement.wsgi:application --bind 0.0.0.0:8000