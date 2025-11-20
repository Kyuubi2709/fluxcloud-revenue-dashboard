from services.flux_api import fetch_apps
from analytics.engine import analyze_apps


if __name__ == "__main__":
    apps = fetch_apps()
    stats = analyze_apps(apps, nodes=[])
    print(stats)
