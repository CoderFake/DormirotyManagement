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