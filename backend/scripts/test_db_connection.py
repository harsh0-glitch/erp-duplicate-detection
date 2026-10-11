import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import text
from app.config import settings
from app.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("db_test")


def mask_connection_url(url: str) -> str:
    """Mask password in connection URL for safe logging."""
    try:
        if "@" in url and "://" in url:
            prefix, rest = url.split("://", 1)
            user_info, host_info = rest.split("@", 1)
            if ":" in user_info:
                user, _ = user_info.split(":", 1)
                return f"{prefix}://{user}:********@{host_info}"
        return url
    except Exception:
        return "[MASKED_URL]"


def check_connection():
    masked_url = mask_connection_url(settings.DATABASE_URL)
    print("=" * 60)
    print(" Supabase PostgreSQL Connection Test")
    print("=" * 60)
    print(f"Target Database URL: {masked_url}")
    print("\nAttempting connection and executing 'SELECT 1;'...")

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;")).scalar()
            version_str = conn.execute(text("SELECT version();")).scalar()

            if result == 1:
                print("\n[SUCCESS] Successfully connected to PostgreSQL!")
                print(f"PostgreSQL Version: {version_str}")
                print("\nDatabase configuration is ready for Stage 3 (Models & Migrations).")
                print("=" * 60)
                return True
            else:
                print(f"\n[FAILURE] Unexpected query result: {result}")
                return False

    except Exception as exc:
        print("\n[FAILURE] Unable to connect to Supabase PostgreSQL.")
        print(f"Error details: {exc}")
        print("\nTroubleshooting Checklist:")
        print("  1. Verify credentials in your .env file.")
        print("  2. If using Supabase Connection Pooler, ensure port is 6543.")
        print("  3. If using Direct Connection, ensure port is 5432 (requires IPv6 or Supabase IPv4 addon).")
        print("  4. Ensure your password does not contain unescaped special characters (e.g. '@', ':', '/')")
        print("     URL-encode special characters if necessary (e.g., %21 for '!').")
        print("  5. Verify ?sslmode=require is appended to the connection string.")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
