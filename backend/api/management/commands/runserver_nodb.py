"""
Management command to run the development server without requiring a PostgreSQL connection.

This command switches the default DATABASES['default'] to an in-memory SQLite database before
starting the server. It enables verifying non-database endpoints (like /health and /api/health)
even when the platform_database service is not reachable.

Usage:
    python manage.py runserver_nodb 0.0.0.0:8000
"""

from django.conf import settings
from django.core.management.commands.runserver import Command as RunserverCommand


# PUBLIC_INTERFACE
class Command(RunserverCommand):
    """Run dev server without PostgreSQL by using in-memory SQLite."""

    help = (
        "Run the development server without requiring PostgreSQL by switching the default "
        "database to in-memory SQLite. Useful for verifying /health and /api/health when "
        "platform_database is not reachable."
    )

    def handle(self, *args, **options):
        # Switch default DB to SQLite to avoid connection attempts to PostgreSQL during startup checks.
        settings.DATABASES["default"] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
        return super().handle(*args, **options)
