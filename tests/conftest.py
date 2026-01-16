import os

# Ensure test environment is set before application/settings import
os.environ.setdefault("ENVIRONMENT", "test")

try:
    from configs.settings import get_settings

    # Refresh cached settings after forcing ENVIRONMENT
    get_settings.cache_clear()
except Exception:
    # If settings are not importable yet, allow tests to proceed
    pass
