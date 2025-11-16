# Fork-specific migration for usage tracking feature
# This migration is idempotent and safe to run multiple times
# It handles both fresh installs and upgrades from old implementation

from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion


def table_exists(table_name):
    """Check if a table exists in the database (SQLite compatible)"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table' AND name=?
        """, [table_name])
        return cursor.fetchone()[0] > 0


def column_exists(table_name, column_name):
    """Check if a column exists in a table (SQLite compatible)"""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns


def migrate_old_usage_data(apps, schema_editor):
    """
    Migrate data from old implementation (Bookmark.access_count) to new (BookmarkUsage).
    Only runs if old access_count column exists.
    """
    # Check if we need to migrate
    if not column_exists('bookmarks_bookmark', 'access_count'):
        print("  → No old access_count data to migrate")
        return

    if not table_exists('bookmarks_bookmarkusage'):
        print("  → BookmarkUsage table doesn't exist yet, skipping data migration")
        return

    Bookmark = apps.get_model('bookmarks', 'Bookmark')
    BookmarkUsage = apps.get_model('bookmarks', 'BookmarkUsage')

    # Migrate old usage counts to new system (attributed to bookmark owner)
    migrated_count = 0
    for bookmark in Bookmark.objects.filter(access_count__gt=0):
        BookmarkUsage.objects.get_or_create(
            bookmark=bookmark,
            user=bookmark.owner,
            defaults={'access_count': bookmark.access_count}
        )
        migrated_count += 1

    print(f"  → Migrated {migrated_count} bookmark usage records")


def remove_old_access_count(apps, schema_editor):
    """
    Remove the old access_count field from Bookmark model.
    Only runs if the column still exists.
    """
    if column_exists('bookmarks_bookmark', 'access_count'):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE bookmarks_bookmark DROP COLUMN access_count")
        print("  → Removed old access_count column from Bookmark")
    else:
        print("  → Old access_count column already removed")


def add_usage_tracking_if_missing(apps, schema_editor):
    """
    Add enable_usage_tracking field to UserProfile if it doesn't exist.
    This handles cases where migration 9999 already ran without this field.
    """
    if not column_exists('bookmarks_userprofile', 'enable_usage_tracking'):
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE bookmarks_userprofile ADD COLUMN enable_usage_tracking BOOLEAN DEFAULT 0 NOT NULL"
            )
        print("  → Added enable_usage_tracking column to UserProfile")
    else:
        print("  → enable_usage_tracking column already exists")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("bookmarks", "0051_fix_normalized_url"),
    ]

    operations = [
        # Add enable_usage_tracking field to UserProfile
        migrations.AddField(
            model_name="userprofile",
            name="enable_usage_tracking",
            field=models.BooleanField(default=False),
        ),

        # Create BookmarkUsage table (only if it doesn't exist)
        migrations.CreateModel(
            name="BookmarkUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("access_count", models.IntegerField(default=0)),
                ("last_accessed", models.DateTimeField(auto_now=True)),
                (
                    "bookmark",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="bookmarks.bookmark",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),

        # Add index for efficient sorting
        migrations.AddIndex(
            model_name="bookmarkusage",
            index=models.Index(
                fields=["user", "-access_count"], name="bookmarks_b_user_id_8c5f6d_idx"
            ),
        ),

        # Add unique constraint
        migrations.AlterUniqueTogether(
            name="bookmarkusage",
            unique_together={("bookmark", "user")},
        ),

        # Migrate old data from Bookmark.access_count
        migrations.RunPython(
            migrate_old_usage_data,
            reverse_code=migrations.RunPython.noop,
        ),

        # Remove old access_count column
        migrations.RunPython(
            remove_old_access_count,
            reverse_code=migrations.RunPython.noop,
        ),

        # Add enable_usage_tracking if missing (for databases where migration already ran)
        migrations.RunPython(
            add_usage_tracking_if_missing,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
