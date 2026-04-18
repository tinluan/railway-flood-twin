import sys
from pathlib import Path
import os
from datetime import datetime, timedelta
from src.utils.paths import paths

def check_project_health():
    """Performs a diagnostic check on the project infrastructure."""
    print("\n--- Project Health Check ---")
    all_ok = True

    # 1. Environment Check
    print("\n[1/4] Environment Config:")
    if not (paths.ROOT / ".env").exists():
        print("  [FAIL] MISSING: .env file")
        all_ok = False
    else:
        print("  [OK] .env file found")
        from dotenv import load_dotenv
        load_dotenv()
        for key in ["DATABASE_URL", "DATA_ROOT"]:
            if not os.getenv(key):
                print(f"  [FAIL] MISSING: '{key}' variable in .env")
                all_ok = False
            else:
                print(f"  [OK] '{key}' is configured")

    # 2. Local Environment Check
    print("\n[2/4] Python Environment:")
    if not (paths.ROOT / ".conda").exists():
        print("  [FAIL] MISSING: Local '.conda' environment")
        all_ok = False
    else:
        print("  [OK] '.conda' environment found")

    # 3. Data Link Check
    print("\n[3/4] Shared Data Connection:")
    if not paths.DATA.exists():
        print(f"  [FAIL] UNREACHABLE: Data root at {paths.DATA}")
        print("     Check your Google Drive connection or DATA_ROOT in .env")
        all_ok = False
    else:
        print(f"  [OK] Data root is reachable: {paths.DATA}")

    # 4. Backup Status
    print("\n[4/4] Database Backup Status:")
    backup_dir = paths.DATA / "backups"
    if not backup_dir.exists():
        print("  [WARN] WARNING: No 'backups' folder found on data root yet.")
    else:
        backups = list(backup_dir.glob("*.sql"))
        if not backups:
            print("  [WARN] WARNING: No .sql backup files found.")
        else:
            latest_backup = max(backups, key=os.path.getmtime)
            mtime = datetime.fromtimestamp(os.path.getmtime(latest_backup))
            age = datetime.now() - mtime
            print(f"  [OK] Latest backup: {latest_backup.name}")
            print(f"     Last updated: {mtime.strftime('%Y-%m-%d %H:%M')}")
            if age > timedelta(days=7):
                print("  [WARN] BACKUP STALE: Latest backup is older than 7 days.")
            else:
                print("  [OK] Backup is fresh.")

    print("\n--- Summary ---")
    if all_ok:
        print("SUCCESS Project is HEALTHY and ready for analysis.")
    else:
        print("ERROR Issues found. Please fix the items marked with [FAIL].")

if __name__ == "__main__":
    try:
        check_project_health()
    except Exception as e:
        print(f"ERROR during health check: {e}")
        sys.exit(1)
