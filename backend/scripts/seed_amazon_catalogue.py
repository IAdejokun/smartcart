"""Seed the products table with a curated mini-catalogue from Amazon Reviews 2023.

Strategy:
- Pull metadata for 5 categories that have visual product cards (so the storefront
  looks good): Electronics, Books, Home_and_Kitchen, Beauty_and_Personal_Care,
  Toys_and_Games.
- Take the top ~160 products per category by review count (= popularity bias).
- ~800 products total. Small enough that DRL learning is visible during demos,
  large enough that the storefront doesn't feel toy.

Source: McAuley Lab Amazon Reviews 2023 (Hugging Face datasets).
https://amazon-reviews-2023.github.io/

Run from backend/:
    python -m scripts.seed_amazon_catalogue
"""
from __future__ import annotations

import logging
import random
import sys
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models.product import Product


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed")


CATEGORIES = [
    "Electronics",
    "Books",
    "Home_and_Kitchen",
    "Beauty_and_Personal_Care",
    "Toys_and_Games",
]
PRODUCTS_PER_CATEGORY = 160


def fetch_category(category: str, limit: int) -> list[dict]:
    """Loads top-`limit` products by review count from a category."""
    from datasets import load_dataset

    log.info("Loading metadata stream for category=%s", category)
    ds = load_dataset(
        "McAuley-Lab/Amazon-Reviews-2023",
        f"raw_meta_{category}",
        split="full",
        trust_remote_code=True,
        streaming=True,
    )

    candidates: list[dict] = []
    seen = 0
    for row in ds:
        seen += 1
        if seen > 50_000:
            break
        if not row.get("title") or not row.get("average_rating"):
            continue
        if not row.get("price"):
            continue
        try:
            price = float(row["price"])
        except (ValueError, TypeError):
            continue
        if price <= 0 or price > 5000:
            continue

        # Amazon Reviews 2023 images schema: dict-of-lists with parallel arrays
        # for thumb/large/hi_res/variant. We want the first 'large' URL.
        images = row.get("images") or {}
        image_urls = images.get("large") or images.get("thumb") or []
        primary_image = image_urls[0] if image_urls else None

        candidates.append({
            "asin": row["parent_asin"],
            "title": row["title"][:500],
            "category": category,
            "price": Decimal(f"{price:.2f}"),
            "avg_rating": float(row["average_rating"]),
            "review_count": int(row.get("rating_number") or 0),
            "extra_data": {
                "store": row.get("store"),
                "main_category": row.get("main_category"),
                "features": (row.get("features") or [])[:5],
                "description": (row.get("description") or [])[:3],
                "image_url": primary_image,
            },
        })

    candidates.sort(key=lambda r: r["review_count"], reverse=True)
    return candidates[:limit]

def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(func.count()).select_from(Product)) or 0
        if existing > 0:
            log.info("Products table already has %d rows — skipping seed", existing)
            log.info("To force reseed, truncate the table first.")
            return

        all_products: list[dict] = []
        for category in CATEGORIES:
            rows = fetch_category(category, PRODUCTS_PER_CATEGORY)
            log.info("  → %d products selected from %s", len(rows), category)
            all_products.extend(rows)

        random.shuffle(all_products)                     # avoid category-clumped insertion order

        # Bulk upsert with on_conflict — survives partial reruns gracefully.
        # We insert in chunks so a single bad row doesn't roll back the lot.
        CHUNK = 100
        for i in range(0, len(all_products), CHUNK):
            chunk = all_products[i : i + CHUNK]
            stmt = pg_insert(Product).values(chunk).on_conflict_do_nothing(
                index_elements=["asin"]
            )
            db.execute(stmt)
            db.commit()
            log.info("Inserted chunk %d–%d", i, i + len(chunk))

        total = db.scalar(select(func.count()).select_from(Product)) or 0
        log.info("✓ Seed complete. Catalogue size: %d products.", total)

    except KeyboardInterrupt:
        log.warning("Seed interrupted by user")
        db.rollback()
        sys.exit(1)
    except Exception:
        log.exception("Seed failed")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()