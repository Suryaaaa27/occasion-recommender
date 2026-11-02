
import pytest

from backend.data_loader import load_products
from backend.recommender import OccasionRecommender


@pytest.fixture(scope="module")
def recommender():
    return OccasionRecommender()


def test_catalog_contains_eligible_products():
    products = load_products()

    assert len(products) > 0
    assert all(product["title"] for product in products)
    assert all(product["status"] == "ACTIVE" for product in products)
    assert all(product["is_approved"] for product in products)
    assert all(product["stock"] > 0 for product in products)


def test_recommendations_return_requested_count(recommender):
    results = recommender.recommend(
        "Diwali gifts and festive hampers",
        top_k=5,
    )

    assert len(results) == 5


def test_diwali_products_rank_highly(recommender):
    results = recommender.recommend(
        "Diwali gifts and festive hampers",
        top_k=5,
    )

    titles = [item["title"].lower() for item in results]

    assert "diwali luxury gift hampers" in titles[:2]


def test_empty_query_returns_no_results(recommender):
    assert recommender.recommend("") == []
    assert recommender.recommend("   ") == []


def test_price_filter_is_respected(recommender):
    results = recommender.recommend(
        "thoughtful gift",
        top_k=10,
        max_price=1000,
    )

    assert all(item["price"] <= 1000 for item in results)


def test_invalid_price_range_raises_error(recommender):
    with pytest.raises(ValueError):
        recommender.recommend(
            "birthday gift",
            min_price=2000,
            max_price=500,
        )


def test_result_scores_are_valid(recommender):
    results = recommender.recommend("wedding gift", top_k=5)

    assert results

    for item in results:
        assert 0.0 <= item["score"] <= 1.0
        assert 0.0 <= item["semantic_score"] <= 1.0
        assert 0.0 <= item["tfidf_score"] <= 1.0


def test_limit_is_capped(recommender):
    results = recommender.recommend("gifts", top_k=100)

    assert len(results) <= 50
