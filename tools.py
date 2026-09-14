"""Week 7 Day 2: The three tools, each working standalone."""
import json
from pathlib import Path

import httpx
from anthropic import Anthropic

# Mock internal data standing in for Drupal Commerce + Yotpo.
# In production these would be live API calls.
MOCK_DATA = Path("mock_data.json")


def _load_mock() -> dict:
    if not MOCK_DATA.exists():
        # Seed with a couple of example SKUs
        seed = {
            "GM-001": {
                "name": "Garam Masala",
                "inventory": 42,
                "units_sold_30d": 137,
                "avg_daily_sales": 4.6,
                "current_price": 8.99,
                "reorder_point": 30,
                "reviews": [
                    {"rating": 5, "text": "Best garam masala I've found. Fresh and aromatic."},
                    {"rating": 4, "text": "Good but the jar arrived half full once."},
                    {"rating": 5, "text": "Use it weekly. Warm and balanced."},
                ],
            },
            "BB-002": {
                "name": "Berbere",
                "inventory": 12,
                "units_sold_30d": 88,
                "avg_daily_sales": 2.9,
                "current_price": 9.49,
                "reorder_point": 20,
                "reviews": [
                    {"rating": 5, "text": "Authentic heat, complex. Great for doro wat."},
                    {"rating": 3, "text": "Hotter than expected."},
                ],
            },
        }
        MOCK_DATA.write_text(json.dumps(seed, indent=2))
    return json.loads(MOCK_DATA.read_text())


def get_internal_metrics(sku: str) -> dict:
    """Return inventory, sales velocity, price, and reorder point for a SKU."""
    data = _load_mock()
    if sku not in data:
        return {"error": f"SKU {sku} not found"}
    d = data[sku]
    return {
        "sku": sku,
        "name": d["name"],
        "inventory": d["inventory"],
        "units_sold_30d": d["units_sold_30d"],
        "avg_daily_sales": d["avg_daily_sales"],
        "current_price": d["current_price"],
        "reorder_point": d["reorder_point"],
        "days_of_stock_left": round(d["inventory"] / d["avg_daily_sales"], 1),
    }


def get_review_sentiment(sku: str) -> dict:
    """Summarize review sentiment for a SKU using an LLM over the review text."""
    data = _load_mock()
    if sku not in data:
        return {"error": f"SKU {sku} not found"}
    reviews = data[sku]["reviews"]
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews)

    # Use a cheap model to summarize sentiment themes
    client = Anthropic()
    review_text = "\n".join(f"[{r['rating']}/5] {r['text']}" for r in reviews)
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"Summarize the key themes (positive and negative) in these product reviews in 2 sentences:\n\n{review_text}"
        }],
    )
    return {
        "sku": sku,
        "avg_rating": round(avg_rating, 2),
        "review_count": len(reviews),
        "sentiment_summary": resp.content[0].text.strip(),
    }


def get_competitor_prices(product_name: str) -> dict:
    """Search the web for competitor prices for a product type.

    For learning, this is a simplified mock that returns plausible numbers.
    In production, wire this to a real web search API (Brave, Serper, Tavily).
    """
    # Mock competitor data keyed by product type
    mock_competitors = {
        "Garam Masala": [
            {"vendor": "CompetitorA", "price": 7.49, "size": "2oz"},
            {"vendor": "CompetitorB", "price": 9.99, "size": "2.5oz"},
            {"vendor": "CompetitorC", "price": 6.99, "size": "1.8oz"},
        ],
        "Berbere": [
            {"vendor": "CompetitorA", "price": 8.99, "size": "2oz"},
            {"vendor": "CompetitorB", "price": 11.49, "size": "3oz"},
        ],
    }
    competitors = mock_competitors.get(product_name, [])
    if not competitors:
        return {"product_name": product_name, "competitors": [], "note": "No competitor data found"}
    prices = [c["price"] for c in competitors]
    return {
        "product_name": product_name,
        "competitors": competitors,
        "avg_competitor_price": round(sum(prices) / len(prices), 2),
        "min_competitor_price": min(prices),
        "max_competitor_price": max(prices),
    }


if __name__ == "__main__":
    # Test each tool standalone
    print("=== Internal metrics ===")
    print(json.dumps(get_internal_metrics("GM-001"), indent=2))
    print("\n=== Review sentiment ===")
    print(json.dumps(get_review_sentiment("GM-001"), indent=2))
    print("\n=== Competitor prices ===")
    print(json.dumps(get_competitor_prices("Garam Masala"), indent=2))