import environ

from .base import * # noqa: F403


env = environ.Env()
env.read_env(BASE_DIR / '.env.development', overwrite=True)

DEBUG = env.bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=[])

DATABASES = {
    "default": env.db(),
}
