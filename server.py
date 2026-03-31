"""
Meta Ads API backend server.
Fetches ad-level data from the Meta Marketing API and returns clean JSON.
"""

from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS
import requests

from config import AD_ACCOUNT_ID, ACCESS_TOKEN, META_API_VERSION

app = Flask(__name__)
CORS(app)

META_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}"

# Fields to request from the Meta Ads API
AD_FIELDS = [
    "campaign_name",
    "adset_name",
    "ad_name",
    "spend",
    "actions",
    "action_values",
    "impressions",
    "clicks",
    "ctr",
    "cpc",
    "cpm",
    "reach",
    "date_start",
    "date_stop",
]

# Action types we care about
PURCHASE_ACTION = "offsite_conversion.fb_pixel_purchase"
ADD_TO_CART_ACTION = "offsite_conversion.fb_pixel_add_to_cart"
CHECKOUT_ACTION = "offsite_conversion.fb_pixel_initiate_checkout"


def extract_action_value(actions, action_type):
    """Extract a specific action count from Meta's actions array."""
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == action_type:
            return float(action.get("value", 0))
    return 0


def extract_action_revenue(action_values, action_type):
    """Extract a specific action value (revenue) from Meta's action_values array."""
    if not action_values:
        return 0
    for av in action_values:
        if av.get("action_type") == action_type:
            return float(av.get("value", 0))
    return 0


def parse_ad_row(row):
    """Parse a single row from the Meta API response into clean JSON."""
    spend = float(row.get("spend", 0))
    purchases = extract_action_value(row.get("actions"), PURCHASE_ACTION)
    revenue = extract_action_revenue(row.get("action_values"), PURCHASE_ACTION)
    adds_to_cart = extract_action_value(row.get("actions"), ADD_TO_CART_ACTION)
    checkouts = extract_action_value(row.get("actions"), CHECKOUT_ACTION)
    impressions = int(row.get("impressions", 0))
    clicks = int(row.get("clicks", 0))

    return {
        "day": row.get("date_start", ""),
        "campaign_name": row.get("campaign_name", ""),
        "adset_name": row.get("adset_name", ""),
        "ad_name": row.get("ad_name", ""),
        "spend": round(spend, 2),
        "purchases": int(purchases),
        "revenue": round(revenue, 2),
        "cpp": round(spend / purchases, 2) if purchases > 0 else 0,
        "roas": round(revenue / spend, 2) if spend > 0 else 0,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": round(float(row.get("ctr", 0)), 2),
        "cpc": round(float(row.get("cpc", 0)), 2),
        "cpm": round(float(row.get("cpm", 0)), 2),
        "reach": int(row.get("reach", 0)),
        "adds_to_cart": int(adds_to_cart),
        "checkouts_initiated": int(checkouts),
    }


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/fetch-meta-data")
def fetch_meta_data():
    """Fetch last 30 days of ad-level data from Meta Ads API."""
    today = datetime.now()
    since = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    until = today.strftime("%Y-%m-%d")

    url = f"{META_BASE_URL}/act_{AD_ACCOUNT_ID}/insights"
    params = {
        "access_token": ACCESS_TOKEN,
        "fields": ",".join(AD_FIELDS),
        "level": "ad",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "time_increment": 1,
        "limit": 500,
    }

    all_rows = []

    try:
        while url:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for row in data.get("data", []):
                all_rows.append(parse_ad_row(row))

            # Handle pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = None  # params are embedded in the next URL

    except requests.exceptions.HTTPError as e:
        error_body = {}
        try:
            error_body = e.response.json()
        except Exception:
            pass
        return jsonify({
            "error": True,
            "message": f"Meta API error: {e.response.status_code}",
            "details": error_body.get("error", {}).get("message", str(e)),
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": True,
            "message": "Failed to connect to Meta API",
            "details": str(e),
        }), 502

    return jsonify({
        "error": False,
        "period": {"since": since, "until": until},
        "total_rows": len(all_rows),
        "fetched_at": datetime.now().isoformat(),
        "data": all_rows,
    })


if __name__ == "__main__":
    print(f"Ad Account: act_{AD_ACCOUNT_ID}")
    print(f"API Version: {META_API_VERSION}")
    print(f"Access Token: {'*' * 8}{ACCESS_TOKEN[-4:] if len(ACCESS_TOKEN) > 4 else '****'}")
    print()
    app.run(host="0.0.0.0", port=5000, debug=True)
