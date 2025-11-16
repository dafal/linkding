# Fork Production Workflow

## Branches Strategy

This fork maintains two branches with different migration strategies:

### `master` Branch
- **Purpose**: For PR to upstream repository
- **Migrations**: Uses standard numbers (0052, 0053)
- **Use**: Keep in sync with PR #1157

### `fork-production` Branch
- **Purpose**: For your production deployment
- **Migrations**: Uses high number (9999) to avoid conflicts
- **Use**: Deploy this branch to production

## Why Two Branches?

**Problem**: While your PR is pending, upstream may add migrations 0052, 0053, 0054... causing conflicts.

**Solution**:
- `master` = clean PR with proper migration numbers
- `fork-production` = stable production with conflict-proof migration 9999

## Migration 9999 Features

The `fork-production` branch contains migration `9999_usage_tracking_fork.py` which:

✅ **Idempotent** - Safe to run multiple times
✅ **Smart** - Detects existing tables/columns
✅ **Data Migration** - Migrates old `Bookmark.access_count` → `BookmarkUsage`
✅ **Cleanup** - Removes old `access_count` column
✅ **Future-proof** - Works alongside future upstream migrations

## Production Deployment

### First Time (Upgrading from old implementation)

Your production currently has:
- Migration 0046 (adds `access_count` to Bookmark)
- Migration 0047 (adds `enable_usage_tracking` to UserProfile)

To upgrade:

```bash
# 1. Backup database first!
./manage.py dumpdata > backup.json

# 2. Checkout fork-production branch
git fetch origin
git checkout fork-production

# 3. Run migration
./manage.py migrate

# Migration 9999 will:
# - Create BookmarkUsage table
# - Migrate existing access_count data (attributed to bookmark owners)
# - Remove old access_count column
# - Everything else stays the same
```

### Verify Migration

```bash
./manage.py showmigrations bookmarks
```

Should show:
```
[X] 0046_bookmark_access_count
[X] 0047_userprofile_enable_usage_tracking
[X] 9999_usage_tracking_fork
```

### Future Updates

When pulling updates from upstream:

```bash
# Stay on fork-production branch
git checkout fork-production

# Merge upstream changes (may include new migrations 0052, 0053, 0054...)
git pull upstream master

# Run migrations - Django will run any new upstream migrations
./manage.py migrate

# Migration 9999 is already done, so it skips
# New upstream migrations (if any) run normally
```

## Syncing with Upstream

```bash
# Update fork-production with upstream changes
git checkout fork-production
git pull upstream master
./manage.py migrate

# The beauty: upstream migrations and your 9999 coexist peacefully!
```

## If PR Gets Accepted

If/when your PR is merged into upstream:

```bash
# Upstream will likely renumber your migrations
# Switch back to upstream master
git remote add upstream https://github.com/sissbruecker/linkding.git
git fetch upstream
git checkout master
git reset --hard upstream/master

# Your production can now follow upstream directly
# (Migration 9999 won't conflict since tables already exist)
```

## Troubleshooting

### "Table already exists" Error

Migration 9999 should prevent this, but if it happens:

```bash
# Mark migration as fake (already applied manually)
./manage.py migrate bookmarks 9999 --fake
```

### Checking Migration Status

```bash
# See what's applied
./manage.py showmigrations bookmarks

# See what would run
./manage.py migrate --plan
```

### Rolling Back (Emergency)

```bash
# Restore from backup
./manage.py loaddata backup.json

# Or rollback migration
./manage.py migrate bookmarks 0047
```

## Summary

- ✅ **Production**: Use `fork-production` branch (migration 9999)
- ✅ **PR/Upstream**: Keep `master` branch (migrations 0052/0053)
- ✅ **Updates**: Pull upstream into `fork-production` anytime
- ✅ **Safety**: Migration 9999 is idempotent and smart
- ✅ **Future**: No conflicts with upstream migrations 0052+

---

**Questions?** Check migration file `bookmarks/migrations/9999_usage_tracking_fork.py` for implementation details.
