"""Finds businesses with the Google Places API (New) Text Search."""
import re
import time

import requests

from . import config

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Phone, website and rating fields put each request in the "Text Search Enterprise" price tier,
# which has a smaller free monthly allowance than basic search. Each request returns up to 20 businesses.
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.businessStatus",
    "places.googleMapsUri",
    "nextPageToken",
])


class PlacesError(Exception):
    pass


def search(category: str, city: str, pages: int = 1) -> list[dict]:
    """Return businesses matching e.g. category="gyms", city="Jaipur". Up to 20 per page, max 3 pages."""
    if not config.GOOGLE_PLACES_API_KEY:
        raise PlacesError("GOOGLE_PLACES_API_KEY is missing in .env")

    headers = {
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {"textQuery": f"{category} in {city}", "pageSize": 20}
    results = []
    for _ in range(min(pages, 3)):
        resp = requests.post(SEARCH_URL, json=body, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise PlacesError(f"Places API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        results += [_to_lead(p, category, city) for p in data.get("places", [])]
        token = data.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
        time.sleep(2)  # the next page token takes a moment to become valid
    return results


def is_good_fit(lead: dict, business_status: str) -> bool:
    """Small vendors who are open, reachable by phone, and busy enough to afford a website."""
    return (
        business_status == "OPERATIONAL"
        and bool(lead["intl_phone"])
        and config.MIN_REVIEWS <= lead["reviews"] <= config.MAX_REVIEWS
    )


def _to_lead(place: dict, category: str, city: str) -> dict:
    lead = {
        "place_id": place["id"],
        "name": place.get("displayName", {}).get("text", ""),
        "category": category,
        "city": city,
        "address": place.get("formattedAddress", ""),
        "phone": place.get("nationalPhoneNumber", ""),
        "intl_phone": re.sub(r"\D", "", place.get("internationalPhoneNumber", "")),
        "website": place.get("websiteUri", ""),
        "rating": place.get("rating") or 0,
        "reviews": place.get("userRatingCount") or 0,
        "maps_url": place.get("googleMapsUri", ""),
    }
    lead["_business_status"] = place.get("businessStatus", "")
    return lead
