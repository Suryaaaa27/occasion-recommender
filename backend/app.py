from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.recommender import OccasionRecommender

app = Flask(__name__)
CORS(app)

recommender = OccasionRecommender()


@app.get("/")
def home():
    return jsonify({
        "message": "Occasion-Based Product Recommendation API",
        "status": "running",
        "eligible_products": len(recommender.products),
        "endpoints": {
            "health": "/api/health",
            "recommend": "/api/recommend?q=Diwali%20gifts",
            "categories": "/api/categories",
        },
    })


@app.get("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "eligible_products": len(recommender.products),
        "model": recommender.model_name,
    })


@app.get("/api/categories")
def categories():
    values = sorted({
        product["category"]
        for product in recommender.products
        if product.get("category")
    })
    return jsonify({"categories": values})


@app.get("/api/recommend")
def recommend():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "error": "Please provide a search query using the q parameter."
        }), 400

    try:
        top_k = int(request.args.get("limit", 12))
        min_price_arg = request.args.get("min_price")
        max_price_arg = request.args.get("max_price")
        category = request.args.get("category") or None

        min_price = (
            float(min_price_arg)
            if min_price_arg is not None
            else None
        )
        max_price = (
            float(max_price_arg)
            if max_price_arg is not None
            else None
        )

        if min_price is not None and min_price < 0:
            return jsonify({"error": "Minimum price cannot be negative."}), 400

        if max_price is not None and max_price < 0:
            return jsonify({"error": "Maximum price cannot be negative."}), 400

        results = recommender.recommend(
            query=query,
            top_k=top_k,
            category=category,
            min_price=min_price,
            max_price=max_price,
        )

        return jsonify({
            "query": query,
            "count": len(results),
            "results": results,
        })

    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (TypeError, OverflowError):
        return jsonify({"error": "Invalid search parameters."}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
