import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = PROJECT_ROOT / "data" / "products.json"


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to a float without crashing on invalid input."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def first_available(*values: Any) -> Any:
    """Return the first value that is not None or an empty string."""
    for value in values:
        if value is not None and value != "":
            return value
    return None


def normalize_files(raw_files: Any, main_image: Any = None) -> list[Any]:
    """
    Normalize product media into a list.

    Preserve an existing files list. If the source only provides mainImage,
    represent that image as a file entry without changing the source JSON.
    """
    if isinstance(raw_files, list):
        files = raw_files.copy()
    elif isinstance(raw_files, dict):
        files = [raw_files]
    else:
        files = []

    if not files and main_image:
        files = [{"url": str(main_image).strip()}]

    return files


def get_image_url(files: list[Any], main_image: Any = None) -> str:
    """Extract a displayable image URL from available product media."""
    if main_image:
        return str(main_image).strip()

    for item in files:
        if isinstance(item, str) and item.strip():
            return item.strip()

        if isinstance(item, dict):
            candidate = (
                item.get("url")
                or item.get("src")
                or item.get("path")
            )
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

    return ""


def infer_category(name: str, description: str) -> str:
    """
    Infer a readable display category when the source does not provide
    a usable human-readable category description.
    """
    text = f"{name} {description}".lower()

    category_rules = [
        (
            "Flowers & Bouquets",
            ["flower", "rose", "lily", "tulip", "bouquet", "floral"],
        ),
        (
            "Chocolates & Sweets",
            ["chocolate", "cocoa", "sweet", "candy", "truffle"],
        ),
        (
            "Gift Hampers",
            ["hamper", "dry fruit", "gift basket", "assorted box"],
        ),
        (
            "Watches & Accessories",
            ["watch", "bracelet", "jewellery", "jewelry", "necklace", "ring"],
        ),
        (
            "Fashion & Apparel",
            ["t-shirt", "tshirt", "shirt", "dress", "clothing", "apparel"],
        ),
        (
            "Fragrance & Self-care",
            ["perfume", "fragrance", "scent", "skincare", "self-care"],
        ),
        (
            "Gift Accessories",
            ["gift wrapping", "gift box", "ribbon", "wrapping paper"],
        ),
        (
            "Personalized Gifts",
            [
                "personalized",
                "personalised",
                "customized",
                "customised",
                "engraved",
            ],
        ),
        (
            "Home & Lifestyle",
            ["candle", "home decor", "decor", "plant", "mug", "photo frame"],
        ),
    ]

    for category, keywords in category_rules:
        if any(keyword in text for keyword in keywords):
            return category

    return "Gifts & Lifestyle"


def normalize_product(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Map source product fields into a consistent schema.

    Assignment fields are retained alongside the existing application
    fields so the recommender and frontend remain compatible.
    """
    product_id = first_available(
        raw.get("product_id"),
        raw.get("productId"),
        raw.get("id"),
    )

    vendor_id = first_available(
        raw.get("vendor_id"),
        raw.get("vendorId"),
        raw.get("shopId"),
    )

    vendor_category = first_available(
        raw.get("vendor_category"),
        raw.get("vendorCategory"),
    )

    vendor_category_desc = first_available(
        raw.get("vendor_category_desc"),
        raw.get("vendorCategoryDesc"),
    )

    title_value = first_available(raw.get("title"), raw.get("name"))
    title = str(title_value or "").strip()

    description = str(
        raw.get("description") or raw.get("shortDescription") or ""
    ).strip()

    short_description = str(
        raw.get("shortDescription") or description
    ).strip()

    files = normalize_files(
        raw.get("files"),
        raw.get("mainImage"),
    )
    image = get_image_url(files, raw.get("mainImage"))

    raw_status = str(raw.get("status") or "ACTIVE").upper()

    is_approved = raw.get("isApproved", True)
    if isinstance(is_approved, str):
        is_approved = (
            is_approved.strip().lower() in {"true", "1", "yes"}
        )

    stock_value = raw.get("stock")
    try:
        stock = int(stock_value) if stock_value is not None else 1
    except (TypeError, ValueError):
        stock = 0

    display_category = (
        str(vendor_category_desc).strip()
        if vendor_category_desc
        else infer_category(title, description)
    )

    brand = str(raw.get("brand") or "").strip()

    search_parts = [
        title,
        description,
        short_description,
        brand,
        str(vendor_category or ""),
        str(vendor_category_desc or ""),
        display_category,
    ]

    search_text = " ".join(
        part.strip() for part in search_parts if part.strip()
    )

    return {
        
        "product_id": str(product_id) if product_id is not None else "",
        "vendor_id": vendor_id,
        "vendor_category": vendor_category,
        "vendor_category_desc": vendor_category_desc,
        "title": title,
        "description": description,
        "files": files,

        
        "id": str(product_id) if product_id is not None else "",
        "category": display_category,
        "short_description": short_description,
        "image": image,
        "brand": brand,
        "price": safe_float(raw.get("price")),
        "discount_percentage": safe_float(
            raw.get("discountPercentage")
        ),
        "stock": stock,
        "status": raw_status,
        "is_approved": bool(is_approved),
        "deleted_at": raw.get("deletedAt"),
        "source_category_id": raw.get("categoryId"),
        "search_text": search_text,
    }


def load_products(
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Load, normalize, and optionally filter the JSON product catalog."""
    path = Path(catalog_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Product catalog not found: {path}\n"
            "Place the supplied JSON file at backend/data/products.json."
        )

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        for key in ("products", "data", "items"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break

    if not isinstance(payload, list):
        raise ValueError(
            "The product catalog must contain a JSON list of products."
        )

    products = [
        normalize_product(item)
        for item in payload
        if isinstance(item, dict)
    ]

    if active_only:
        products = [
            product
            for product in products
            if product["title"]
            and product["status"] == "ACTIVE"
            and product["is_approved"]
            and not product["deleted_at"]
            and product["stock"] > 0
        ]

    return products
