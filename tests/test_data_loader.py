
import json

from backend.data_loader import load_products, normalize_product


def test_assignment_fields_are_present():
    product = normalize_product({
        "product_id": "p-101",
        "vendor_id": "v-202",
        "vendor_category": "gift-hampers",
        "vendor_category_desc": "Gift Hampers",
        "title": "Festive Gift Box",
        "description": "A gift box for festive occasions.",
        "files": [{"url": "https://example.com/gift.jpg"}],
    })

    assert product["product_id"] == "p-101"
    assert product["vendor_id"] == "v-202"
    assert product["vendor_category"] == "gift-hampers"
    assert product["vendor_category_desc"] == "Gift Hampers"
    assert product["title"] == "Festive Gift Box"
    assert product["description"] == "A gift box for festive occasions."
    assert product["files"] == [
        {"url": "https://example.com/gift.jpg"}
    ]


def test_source_catalog_aliases_are_mapped():
    product = normalize_product({
        "id": "source-123",
        "shopId": "shop-456",
        "categoryId": "category-789",
        "name": "Flower Bouquet",
        "description": "Fresh flowers for gifting.",
        "mainImage": "https://example.com/flower.jpg",
        "status": "ACTIVE",
        "isApproved": True,
        "stock": 5,
    })

    assert product["product_id"] == "source-123"
    assert product["id"] == "source-123"
    assert product["vendor_id"] == "shop-456"
    assert product["title"] == "Flower Bouquet"
    assert product["source_category_id"] == "category-789"
    assert product["image"] == "https://example.com/flower.jpg"
    assert product["files"] == [
        {"url": "https://example.com/flower.jpg"}
    ]


def test_camel_case_assignment_aliases_are_supported():
    product = normalize_product({
        "productId": "p-303",
        "vendorId": "v-404",
        "vendorCategory": "flowers",
        "vendorCategoryDesc": "Flowers & Bouquets",
        "title": "Rose Bouquet",
        "description": "A rose bouquet.",
        "files": [],
    })

    assert product["product_id"] == "p-303"
    assert product["vendor_id"] == "v-404"
    assert product["vendor_category"] == "flowers"
    assert product["vendor_category_desc"] == "Flowers & Bouquets"


def test_missing_vendor_fields_are_not_fabricated():
    product = normalize_product({
        "id": "p-505",
        "name": "Simple Gift",
        "description": "A thoughtful gift.",
    })

    assert product["vendor_category"] is None
    assert product["vendor_category_desc"] is None


def test_main_image_is_adapted_to_files():
    product = normalize_product({
        "id": "p-606",
        "name": "Photo Frame",
        "mainImage": "https://example.com/frame.jpg",
    })

    assert product["files"] == [
        {"url": "https://example.com/frame.jpg"}
    ]
    assert product["image"] == "https://example.com/frame.jpg"


def test_real_catalog_has_required_normalized_keys():
    products = load_products()

    assert products

    required_keys = {
        "product_id",
        "vendor_id",
        "vendor_category",
        "vendor_category_desc",
        "title",
        "description",
        "files",
    }

    for product in products:
        assert required_keys.issubset(product.keys())
        assert isinstance(product["files"], list)
        assert product["title"]


def test_normalization_does_not_mutate_source_object():
    source = {
        "id": "p-707",
        "name": "Gift Box",
        "mainImage": "https://example.com/box.jpg",
    }
    original = json.loads(json.dumps(source))

    normalize_product(source)

    assert source == original
