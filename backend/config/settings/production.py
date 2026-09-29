import environ

from .base import *  # noqa: F403

env = environ.Env()
env.read_env(str(BASE_DIR / ".env.production"), overwrite=True)

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

DATABASES = {
    "default": env.db(),
}

# ---------------------------------------------------------------------
# HTTPS / امنیت شبکه
# ---------------------------------------------------------------------

# چون پشت nginx (یا هر reverse proxy دیگه) هستیم، TLS اونجا terminate
# می‌شه و درخواست به Django به‌صورت http داخلی می‌رسه. این هدر بهمون
# می‌گه که "اصل" درخواست https بوده، وگرنه SECURE_SSL_REDIRECT و
# چک‌های امنیتی دیگه فکر می‌کنن همه‌چیز http‌ه.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# HSTS: اول با یه مقدار کوچیک شروع کن (مثلاً یه روز)، بعد از این‌که
# مطمئن شدی HTTPS همه‌جا درست کار می‌کنه، بزرگش کن (یه ماه، بعد یه سال).
# اگه اشتباهی خیلی زود مقدار بزرگ بذاری و بعد بخوای HTTPS رو خاموش کنی،
# مرورگرهایی که قبلاً این هدر رو دیدن تا مدت‌ها اصلاً اجازه‌ی http نمی‌دن.
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=86400)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = False  # فقط بعد از اطمینان کامل از HTTPS فعالش کن

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# INSTALLED_APPS += ["corsheaders"]
# MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware") # باید اول از همه باشه
# CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])

# Static files (Whitenoise)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # بعد از SecurityMiddleware

STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

ADMINS = [
    tuple(pair.split(":", 1))
    for pair in env.list("DJANGO_ADMINS", default=[])
]

EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("DJANGO_EMAIL_HOST", default="")
EMAIL_PORT = env.int("DJANGO_EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("DJANGO_EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("DJANGO_EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("DJANGO_EMAIL_USE_TLS", default=True)
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default="noreply@example.com")