const API_BASE = "http://127.0.0.1:5000/api";

const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchButton = document.getElementById("search-button");
const productGrid = document.getElementById("product-grid");
const resultsSummary = document.getElementById("results-summary");
const statusMessage = document.getElementById("status-message");
const emptyState = document.getElementById("empty-state");
const categoryFilter = document.getElementById("category-filter");
const priceFilter = document.getElementById("price-filter");
const occasionButtons = document.querySelectorAll("[data-query]");

let currentQuery = "";
let requestController = null;
let requestSequence = 0;

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };

    return entities[character];
  });
}

function formatPrice(value) {
  const price = Number(value);

  if (!Number.isFinite(price)) {
    return "Price unavailable";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(price);
}

function setStatus(message, isError = false) {
  statusMessage.classList.toggle("error", isError);

  statusMessage.innerHTML = `
    <span class="status-symbol" aria-hidden="true">
      ${isError ? "!" : "✳"}
    </span>
    <span>${escapeHTML(message)}</span>
  `;

  statusMessage.hidden = false;
}

function setLoading(isLoading) {
  searchButton.disabled = isLoading;
  searchButton.innerHTML = isLoading
    ? "Searching…"
    : 'Discover <span>→</span>';
}

function getSelectedFilters() {
  const selectedCategory = categoryFilter.value;
  const maxPrice = priceFilter.value;

  return {
    category: selectedCategory,
    maxPrice,
  };
}

function buildRecommendationURL(query) {
  const params = new URLSearchParams({
    q: query,
    limit: "12",
  });

  const { category, maxPrice } = getSelectedFilters();

  if (category) {
    params.set("category", category);
  }

  if (maxPrice) {
    params.set("max_price", maxPrice);
  }

  return `${API_BASE}/recommend?${params.toString()}`;
}

function renderProducts(products) {
  productGrid.replaceChildren();

  emptyState.hidden = products.length !== 0;

  if (products.length === 0) {
    return;
  }

  const markup = products.map((product) => {
    const title = escapeHTML(product.title || "Untitled gift");
    const category = escapeHTML(product.category || "Gift");
    const brand = escapeHTML(product.brand || "Curated selection");
    const description = escapeHTML(
      product.short_description ||
      product.description ||
      "A thoughtful option for your special occasion."
    );

    const imageURL = String(product.image || "");
    const safeImageURL = /^https?:\/\//i.test(imageURL)
      ? escapeHTML(imageURL)
      : "";

    const score = Number(product.score);
    const scoreLabel = Number.isFinite(score)
      ? `${Math.round(Math.max(0, Math.min(1, score)) * 100)}% match`
      : "Recommended";

    const reasons = Array.isArray(product.reasons)
      ? product.reasons
      : [];

    const reasonText = escapeHTML(
      reasons.join(" · ") || "Related to your search"
    );

    const discount = Number(product.discount_percentage);
    const originalPrice =
      Number.isFinite(discount) && discount > 0 && discount < 100
        ? Number(product.price) / (1 - discount / 100)
        : null;

    const imageMarkup = safeImageURL
      ? `<img
          class="product-image"
          src="${safeImageURL}"
          alt="${title}"
          loading="lazy"
          referrerpolicy="no-referrer"
        >`
      : `<div class="product-image-placeholder" aria-hidden="true">✳</div>`;

    return `
      <article class="product-card">
        <div class="product-image-wrap">
          ${imageMarkup}
          <span class="product-badge">${scoreLabel}</span>
        </div>

        <div class="product-content">
          <p class="product-category">${category}</p>
          <h3 class="product-title">${title}</h3>
          <p class="product-brand">${brand}</p>
          <p class="product-description">${description}</p>

          <div class="product-bottom">
            <div class="product-price">
              ${formatPrice(product.price)}
              ${
                originalPrice !== null
                  ? `<span class="product-price-old">${formatPrice(originalPrice)}</span>`
                  : ""
              }
            </div>
            <span class="match-score">${scoreLabel}</span>
          </div>

          <p class="product-reason">${reasonText}</p>
        </div>
      </article>
    `;
  }).join("");

  productGrid.innerHTML = markup;

  productGrid.querySelectorAll(".product-image").forEach((image) => {
    image.addEventListener("error", () => {
      const placeholder = document.createElement("div");
      placeholder.className = "product-image-placeholder";
      placeholder.setAttribute("aria-hidden", "true");
      placeholder.textContent = "✳";
      image.replaceWith(placeholder);
    }, { once: true });
  });
}

async function loadCategories() {
  try {
    const response = await fetch(`${API_BASE}/categories`);

    if (!response.ok) {
      throw new Error("Could not load categories.");
    }

    const data = await response.json();

    for (const category of data.categories || []) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categoryFilter.appendChild(option);
    }
  } catch (error) {
    console.error("Category loading failed:", error);
    setStatus(
      "Categories could not be loaded. You can still search for gifts.",
      true
    );
  }
}

async function searchProducts(query = currentQuery) {
  const cleanQuery = String(query || "").trim();

  if (!cleanQuery) {
    setStatus("Enter an occasion or describe the gift you're looking for.");
    searchInput.focus();
    return;
  }

  currentQuery = cleanQuery;
  searchInput.value = cleanQuery;

  if (requestController) {
    requestController.abort();
  }

  requestController = new AbortController();
  const controller = requestController;
  const sequence = ++requestSequence;

  setLoading(true);
  emptyState.hidden = true;
  productGrid.replaceChildren();

  resultsSummary.textContent = `Finding thoughtful gifts for "${cleanQuery}"…`;
  setStatus("Matching your occasion with relevant products. Please wait.");

  try {
    const response = await fetch(
      buildRecommendationURL(cleanQuery),
      { signal: controller.signal }
    );

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "The recommendation request failed.");
    }

    if (sequence !== requestSequence) {
      return;
    }

    const products = Array.isArray(data.results) ? data.results : [];

    renderProducts(products);

    resultsSummary.textContent = products.length
      ? `${products.length} recommendations for "${cleanQuery}"`
      : `No recommendations for "${cleanQuery}"`;

    if (products.length) {
      setStatus(
        `Found ${products.length} products ranked using semantic similarity, keyword matching, and occasion relevance.`
      );
    } else {
      setStatus(
        "No products matched these filters. Try another search or broaden your price range."
      );
    }

    document.getElementById("recommendations").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    if (sequence !== requestSequence) {
      return;
    }

    console.error("Recommendation request failed:", error);

    resultsSummary.textContent = "Recommendations are temporarily unavailable.";

    setStatus(
      "Could not connect to the recommendation API. Make sure the Flask server is running at http://127.0.0.1:5000.",
      true
    );
  } finally {
    if (sequence === requestSequence) {
      setLoading(false);
      requestController = null;
    }
  }
}

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  searchProducts(searchInput.value);
});

occasionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const query = button.dataset.query;
    searchProducts(query);
  });
});

categoryFilter.addEventListener("change", () => {
  if (currentQuery) {
    searchProducts(currentQuery);
  }
});

priceFilter.addEventListener("change", () => {
  if (currentQuery) {
    searchProducts(currentQuery);
  }
});

loadCategories();
