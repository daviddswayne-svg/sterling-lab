dbip-country-lite.mmdb - IP to country database used by /api/geo (bedrock_api.py) for the homepage greeting.

Source: DB-IP Lite, https://db-ip.com - licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
Attribution is shown in the homepage footer ("IP Geolocation by DB-IP").
Version: October 2026 (dbip-country-lite-2026-10). Refresh occasionally:
  curl -A "Mozilla/5.0" -o x.gz https://download.db-ip.com/free/dbip-country-lite-YYYY-MM.mmdb.gz
  gunzip -c x.gz > dbip-country-lite.mmdb
