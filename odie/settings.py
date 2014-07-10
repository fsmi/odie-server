"""
Django settings for odie project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEPOSIT_AMOUNT = 500 # in cents
PRICE_PER_PAGE = 3   # in cents

# Paths to exam PDFs

WRITTEN_EXAMS_PATH = os.path.join(BASE_DIR, 'written/')
ORAL_EXAMS_PATH = os.path.join(BASE_DIR, 'oral/')

def do_print(print_helper_args):
    raise NotImplementedError(print_helper_args)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'wowsuchsecretwow'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    #'corsheaders',
    'odie',
    'fsmi',
    'prfproto'
)

MIDDLEWARE_CLASSES = (
    #'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
)

ROOT_URLCONF = 'odie.urls'

WSGI_APPLICATION = 'odie.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASE_ROUTERS = ['odie.db_router.DbRouter']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'odie',
    },
    'fsmi': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'fsmi',
    },
    'prfproto': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'prfproto',
    }
}

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

SESSION_COOKIE_HTTPONLY = False

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/web/'

# Cross Origin Resource Sharing
# Allow API access from everywhere
CORS_ORIGIN_ALLOW_ALL = True

# Import host-specific settings
try:
    from odie.local_settings import *
except ImportError:
    pass
