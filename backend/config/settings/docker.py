from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in __import__("os").getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,web",
    ).split(",")
    if host.strip()
]
