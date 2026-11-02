
from __future__ import annotations

import re
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.data_loader import load_products


class OccasionRecommender:
    """
    Hybrid, content-based product recommendation engine.

    Final score =
        0.65 * semantic similarity
        + 0.35 * TF-IDF similarity
        + occasion relevance bonus

    Product embeddings are calculated once during initialization.
    """

    SEMANTIC_WEIGHT = 0.65
    TFIDF_WEIGHT = 0.35
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    OCCASION_KEYWORDS = {
        "birthday": [
            "birthday", "cake", "chocolate", "flowers", "bouquet",
            "personalized", "personalised", "gift hamper", "perfume",
            "watch", "gift box",
        ],
        "wedding": [
            "wedding", "bride", "groom", "couple", "anniversary",
            "flowers", "bouquet", "premium", "luxury", "gift hamper",
        ],
        "diwali": [
            "diwali", "deepavali", "festive", "festival", "dry fruit",
            "sweets", "chocolate", "hamper", "gift box", "traditional",
        ],
        "valentines day": [
            "valentine", "love", "romantic", "romance", "rose",
            "roses", "red rose", "chocolate", "couple", "heart",
            "bouquet", "perfume",
        ],
        "valentine's day": [
            "valentine", "love", "romantic", "romance", "rose",
            "roses", "chocolate", "couple", "heart", "bouquet",
        ],
        "anniversary": [
            "anniversary", "couple", "romantic", "love", "rose",
            "roses", "chocolate", "watch", "perfume", "premium",
        ],
        "mothers day": [
            "mother", "mom", "mum", "flowers", "bouquet", "perfume",
            "self-care", "skincare", "chocolate", "personalized",
        ],
        "fathers day": [
            "father", "dad", "watch", "accessories", "perfume",
            "grooming", "wallet", "premium", "gift set",
        ],
        "raksha bandhan": [
            "rakhi", "raksha bandhan", "brother", "sister",
            "chocolate", "sweets", "gift hamper", "gift box",
        ],
        "rakhi": [
            "rakhi", "raksha bandhan", "brother", "sister",
            "chocolate", "sweets", "gift hamper",
        ],
        "christmas": [
            "christmas", "festive", "festival", "gift box",
            "chocolate", "hamper", "sweets", "premium",
        ],
        "housewarming": [
            "housewarming", "home", "home decor", "plant", "candle",
            "mug", "photo frame", "lifestyle",
        ],
        "farewell": [
            "farewell", "colleague", "office", "professional",
            "watch", "gift set", "personalized", "premium",
        ],
        "graduation": [
            "graduation", "achievement", "congratulations",
            "watch", "personalized", "premium", "gift set",
        ],
        "office party": [
            "office", "colleague", "corporate", "professional",
            "chocolate", "hamper", "gift set", "gift box",
        ],
        "thank you": [
            "thank you", "gratitude", "flowers", "chocolate",
            "bouquet", "gift hamper", "premium",
        ],
        "baby shower": [
            "baby", "newborn", "baby shower", "parent",
            "personalized", "gift hamper", "gift set",
        ],
    }

    def __init__(
        self,
        products: list[dict[str, Any]] | None = None,
        model_name: str | None = None,
    ) -> None:
        self.products = products if products is not None else load_products()

        if not self.products:
            raise ValueError(
                "No eligible products were found in the product catalog."
            )

        self.model_name = model_name or self.MODEL_NAME

        self.product_texts = [
            self._build_product_text(product)
            for product in self.products
        ]

        print(f"Loading semantic model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        print(f"Encoding {len(self.products)} products...")
        self.product_embeddings = self.model.encode(
            self.product_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        self.tfidf_vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=50000,
        )

        self.product_tfidf_matrix = self.tfidf_vectorizer.fit_transform(
            self.product_texts
        )

        print(
            f"Recommendation engine ready with "
            f"{len(self.products)} eligible products."
        )

    @staticmethod
    def _build_product_text(product: dict[str, Any]) -> str:
        """Combine useful normalized fields for both matching methods."""
        fields = [
            product.get("title", ""),
            product.get("category", ""),
            product.get("brand", ""),
            product.get("description", ""),
            product.get("short_description", ""),
        ]

        return " ".join(
            str(field).strip()
            for field in fields
            if field and str(field).strip()
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize punctuation and whitespace for keyword matching."""
        text = text.lower().replace("&", " and ")
        text = re.sub(r"[^a-z0-9\s']", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _detect_occasions(self, query: str) -> list[str]:
        """
        Detect known occasions in the user's query.

        Longer phrases are checked first, so phrases such as
        'Valentine's Day' are handled as a single occasion.
        """
        normalized_query = self._normalize_text(query)
        detected = []

        for occasion in sorted(
            self.OCCASION_KEYWORDS,
            key=len,
            reverse=True,
        ):
            normalized_occasion = self._normalize_text(occasion)

            if re.search(
                rf"\b{re.escape(normalized_occasion)}\b",
                normalized_query,
            ):
                canonical = normalized_occasion
                if canonical not in detected:
                    detected.append(canonical)

        return detected

    def _occasion_score(
        self,
        product: dict[str, Any],
        occasions: list[str],
    ) -> tuple[float, list[str]]:
        if not occasions:
            return 0.0, []

        title = self._normalize_text(product.get("title", ""))
        product_text = self._normalize_text(
            self._build_product_text(product)
        )

        matched_terms = []
        bonus = 0.0

        for occasion in occasions:
            keywords = self.OCCASION_KEYWORDS.get(occasion, [])

           
            occasion_words = occasion.split()
            title_has_occasion = (
                occasion in title
                or all(
                    re.search(rf"\b{re.escape(word)}\b", title)
                    for word in occasion_words
                )
            )

            if title_has_occasion:
                bonus += 0.22

           
            occasion_matches = []
            for keyword in keywords:
                term = self._normalize_text(keyword)
                if term and re.search(
                    rf"\b{re.escape(term)}\b",
                    product_text,
                ):
                    occasion_matches.append(keyword)

            unique_matches = list(dict.fromkeys(occasion_matches))
            matched_terms.extend(unique_matches)

            if unique_matches:
                bonus += min(0.10, len(unique_matches) * 0.025)

        bonus = min(0.30, bonus)

        return bonus, list(dict.fromkeys(matched_terms))[:6]

    @staticmethod
    def _clamp_score(score: float) -> float:
        return float(np.clip(score, 0.0, 1.0))

    def recommend(
        self,
        query: str,
        top_k: int = 12,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return ranked product recommendations for an occasion query."""
        query = str(query or "").strip()

        if not query:
            return []

        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 12

        top_k = max(1, min(top_k, 50))

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise ValueError(
                    "Minimum price cannot be greater than maximum price."
                )

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        semantic_scores = cosine_similarity(
            query_embedding,
            self.product_embeddings,
        )[0]

        query_tfidf = self.tfidf_vectorizer.transform([query])

        tfidf_scores = cosine_similarity(
            query_tfidf,
            self.product_tfidf_matrix,
        )[0]

        occasions = self._detect_occasions(query)
        normalized_category = (
            self._normalize_text(category)
            if category
            else None
        )

        results = []

        for index, product in enumerate(self.products):
            price = float(product.get("price", 0.0))

            if min_price is not None and price < float(min_price):
                continue

            if max_price is not None and price > float(max_price):
                continue

            if normalized_category:
                product_category = self._normalize_text(
                    product.get("category", "")
                )
                if product_category != normalized_category:
                    continue

            semantic_score = self._clamp_score(
                float(semantic_scores[index])
            )
            tfidf_score = self._clamp_score(
                float(tfidf_scores[index])
            )

            hybrid_score = (
                self.SEMANTIC_WEIGHT * semantic_score
                + self.TFIDF_WEIGHT * tfidf_score
            )

            occasion_bonus, matched_terms = self._occasion_score(
                product,
                occasions,
            )

            final_score = min(
                1.0,
                hybrid_score + occasion_bonus,
            )

            reasons = []

            if semantic_score >= 0.40:
                reasons.append("Strong meaning-based match")

            if tfidf_score >= 0.10:
                reasons.append("Relevant keyword match")

            if matched_terms:
                reasons.append(
                    "Occasion match: " + ", ".join(matched_terms[:3])
                )

            if not reasons:
                reasons.append("Related to your search")

            results.append({
                "id": product.get("id", ""),
                "title": product.get("title", ""),
                "category": product.get("category", ""),
                "description": product.get("description", ""),
                "short_description": product.get("short_description", ""),
                "image": product.get("image", ""),
                "brand": product.get("brand", ""),
                "price": price,
                "discount_percentage": product.get(
                    "discount_percentage", 0.0
                ),
                "stock": product.get("stock", 0),
                "score": round(final_score, 4),
                "semantic_score": round(semantic_score, 4),
                "tfidf_score": round(tfidf_score, 4),
                "occasion_bonus": round(occasion_bonus, 4),
                "matched_occasions": occasions,
                "matched_terms": matched_terms,
                "reasons": reasons,
            })

        results.sort(
            key=lambda item: (
                item["score"],
                item["semantic_score"],
                item["tfidf_score"],
            ),
            reverse=True,
        )

        return results[:top_k]


if __name__ == "__main__":
    recommender = OccasionRecommender()

    test_queries = [
        "Birthday gift for someone special",
        "Diwali gifts and festive hampers",
        "Wedding gift for a couple",
        "Romantic gift for Valentine's Day",
    ]

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"Query: {query}")

        for rank, item in enumerate(
            recommender.recommend(query, top_k=5),
            start=1,
        ):
            print(
                f"{rank}. {item['title']} | "
                f"Rs. {item['price']:.2f} | "
                f"Score: {item['score']:.4f}"
            )
            print(f"   Reason: {'; '.join(item['reasons'])}")
