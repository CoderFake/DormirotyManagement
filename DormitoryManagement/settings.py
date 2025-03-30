"""
Django settings for DormitoryManagement project.

Generated by 'django-admin startproject' using Django 5.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""
import ssl
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
ENV = os.getenv("ENVIRONMENT", "dev")

DEBUG = True
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS=[
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8008',
    'http://127.0.0.1:8008',
]

if ENV != "dev":
    DEBUG = False
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split(',')
    CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS').split(',')

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Cài đặt bên thứ 3
    "corsheaders",
    "whitenoise.runserver_nostatic",
    "vnpay",
    "mathfilters",

    # Ứng dụng tùy chỉnh
    "accounts.apps.AccountsConfig",
    "dormitory.apps.DormitoryConfig",
    "registration.apps.RegistrationConfig",
    "payment.apps.PaymentConfig",
    "maintenance.apps.MaintenanceConfig",
    "notification.apps.NotificationConfig",
    "dashboard.apps.DashboardConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "DormitoryManagement.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "DormitoryManagement.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DB_NAME"),
        "USER": os.getenv("MYSQL_DB_USER"),
        "PASSWORD": os.getenv("MYSQL_DB_PASSWORD"),
        "HOST": os.getenv("MYSQL_DB_HOST"),
        "PORT": os.getenv("MYSQL_DB_PORT"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET NAMES 'utf8mb4'",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "vi"

TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Ho_Chi_Minh")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cấu hình Auth tùy chỉnh
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"


# ID của site mặc định
SITE_ID = 1


# Cấu hình email
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Dormitory Management <noreply@dormitory.com>")

# Cấu hình VNPAY
VNPAY_TMN_CODE = os.getenv("VNPAY_TMN_CODE", "")
VNPAY_HASH_SECRET_KEY = os.getenv("VNPAY_HASH_SECRET_KEY", "")
VNPAY_PAYMENT_URL = os.getenv("VNPAY_PAYMENT_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
VNPAY_RETURN_URL = os.getenv("VNPAY_RETURN_URL", "http://localhost:8008/payment/vnpay-return/")
VNPAY_API_URL = os.getenv("VNPAY_API_URL", "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction")

# Cấu hình CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8008",
    "http://127.0.0.1:8008",
]
if ENV != "dev":
    CORS_ALLOWED_ORIGINS.extend(os.environ.get('ALLOWED_HOSTS', "").split(','))