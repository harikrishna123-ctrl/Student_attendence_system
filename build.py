from pathlib import Path
import shutil


PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
PUBLIC_DIR = PROJECT_DIR / "public"

for asset_dir in ("assets", "css", "js"):
    shutil.copytree(
        FRONTEND_DIR / asset_dir,
        PUBLIC_DIR / asset_dir,
        dirs_exist_ok=True
    )
