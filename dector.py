from app_scanner import load_apps

apps = load_apps()

for app_name, exe_path in apps.items():
    print(f"{app_name}: {exe_path}")
