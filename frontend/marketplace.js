
/* =====================================================
   COMMERCEAI — PRODUCT MARKETPLACE
   Top navigation controls product filtering.
   Existing app.js functionality is preserved.
===================================================== */

(function () {
    "use strict";

    const PRODUCT_DATA_URL = "../backend/database/products.json";

    let marketplaceProducts = [];
    let activeCategory = "all";

    const categories = [
        { id: "all", label: "All Products", icon: "fa-border-all" },
        { id: "laptop", label: "Laptops", icon: "fa-laptop" },
        { id: "smartphone", label: "Smartphones", icon: "fa-mobile-screen" },
        { id: "audio", label: "Audio", icon: "fa-headphones" },
        { id: "electronics", label: "Electronics", icon: "fa-camera" },
        { id: "gaming", label: "Gaming", icon: "fa-gamepad" }
    ];

    function escape(value) {
        if (typeof escapeHTML === "function") {
            return escapeHTML(value);
        }

        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function currency(value) {
        if (typeof formatCurrency === "function") {
            return formatCurrency(value);
        }

        return "₹" + Number(value || 0).toLocaleString("en-IN");
    }

    function getName(product) {
        return product.name ||
            product.product_name ||
            product.title ||
            "Product";
    }

    function getCategory(product) {
        return String(product.category || "").toLowerCase();
    }

    function getRating(product) {
        return product.rating ?? "N/A";
    }

    function getReviews(product) {
        return product.reviews ??
            product.review_count ??
            0;
    }

    function getFeatures(product) {
        if (typeof getFeaturesText === "function") {
            return getFeaturesText(product);
        }

        if (Array.isArray(product.features)) {
            return product.features.join(" • ");
        }

        return product.description || "Product details available";
    }

    function matchesCategory(product, category) {
        if (category === "all") return true;

        const value = getCategory(product);

        if (category === "audio") {
            return value.includes("audio") ||
                value.includes("headphone");
        }
        if (category === "smartphone") {
            return value.includes("smartphone") ||
                value === "phone" ||
                value.includes("mobile");
       }

        if (category === "electronics") {
            return value.includes("electronic") ||
                value.includes("camera") ||
                value.includes("tv");
        }

        if (category === "gaming") {
            return value.includes("gaming") ||
                value.includes("console");
        }

        return value.includes(category);
    }

    /* TOP NAVIGATION */

    function updateTopNavigation() {
        document.querySelectorAll(
            ".marketplace-nav .marketplace-category"
        ).forEach(link => {
            const label = link.textContent.trim().toLowerCase();

            const category = categories.find(item =>
                item.label.toLowerCase() === label
            );

            const isSaved = label === "saved items";

            link.classList.toggle(
                "active",
                isSaved
                    ? false
                    : category?.id === activeCategory
            );
        });
    }

    function setupTopNavigation() {
        const links = document.querySelectorAll(
            ".marketplace-nav .marketplace-category"
        );

        links.forEach(link => {
            link.addEventListener("click", function (event) {
                event.preventDefault();

                const label = this.textContent.trim().toLowerCase();

                if (label === "saved items") {
                    if (typeof navigateToPage === "function") {
                        navigateToPage("wishlist");
                    } else {
                        window.location.hash = "wishlist";
                    }

                    return;
                }

                const selectedCategory = categories.find(item =>
                    item.label.toLowerCase() === label
                );

                if (!selectedCategory) return;

                activeCategory = selectedCategory.id;

                if (typeof navigateToPage === "function") {
                    navigateToPage("products");
                } else {
                    window.location.hash = "products";
                }

                updateTopNavigation();
                renderMarketplace();
            });
        });

        updateTopNavigation();
    }

    /* PRODUCT COUNT */

    function renderCategoryFilters() {
        return `
            <div class="marketplace-toolbar">
                <div class="marketplace-count">
                    ${getFilteredProductCount()} products available
                </div>
            </div>
        `;
    }

    function getFilteredProductCount() {
        return marketplaceProducts.filter(product =>
            matchesCategory(product, activeCategory)
        ).length;
    }

    /* PRODUCT CARD */

    function renderProductCard(product, index) {
        const name = getName(product);
        const brand = product.brand || "Brand";
        const price = product.price || 0;
        const rating = getRating(product);
        const reviews = getReviews(product);
        const features = getFeatures(product);

        const productId = product.id ??
            product.product_id ??
            product.sku ??
            name;

        const saved = typeof isInWishlist === "function"
            ? isInWishlist(productId)
            : false;

        const imageHTML = typeof getProductImageHTML === "function"
            ? getProductImageHTML(product, "marketplace-product-image")
            : `<div class="marketplace-product-image">🛍️</div>`;

        return `
            <article class="product-card marketplace-card">

                <div class="marketplace-image-wrapper">

                    ${imageHTML}

                    <button
                        type="button"
                        class="marketplace-heart ${saved ? "saved" : ""}"
                        data-action="wishlist"
                        data-index="${index}"
                        aria-label="Add ${escape(name)} to wishlist"
                        title="${saved ? "Saved" : "Add to wishlist"}"
                    >
                        <i class="${saved ? "fa-solid" : "fa-regular"} fa-heart"></i>
                    </button>

                </div>

                <div class="marketplace-card-content">

                    <div class="marketplace-brand">
                        ${escape(brand)}
                    </div>

                    <h3>${escape(name)}</h3>

                    <div class="marketplace-rating">
                        <i class="fa-solid fa-star"></i>
                        ${escape(rating)}
                        <span>(${escape(reviews)} reviews)</span>
                    </div>

                    <p class="marketplace-features">
                        ${escape(features)}
                    </p>

                    <div class="marketplace-card-bottom">

                        <strong class="marketplace-price">
                            ${currency(price)}
                        </strong>

                        <button
                            type="button"
                            class="marketplace-view-button"
                            data-action="view"
                            data-index="${index}"
                        >
                            View Product
                            <i class="fa-solid fa-arrow-right"></i>
                        </button>

                    </div>

                </div>

            </article>
        `;
    }

    /* RENDER PRODUCTS */

    function renderMarketplace() {
        const container = document.getElementById("productsPageContent");

        if (!container) return;

        const filteredProducts = marketplaceProducts
            .map((product, originalIndex) => ({
                product,
                originalIndex
            }))
            .filter(item =>
                matchesCategory(item.product, activeCategory)
            );

        container.innerHTML = `
            ${renderCategoryFilters()}

            <div class="marketplace-grid">

                ${
                    filteredProducts.length
                        ? filteredProducts.map(item =>
                            renderProductCard(
                                item.product,
                                item.originalIndex
                            )
                        ).join("")
                        : `
                            <div class="marketplace-empty">
                                <i class="fa-solid fa-box-open"></i>
                                <h3>No products found</h3>
                                <p>Try selecting another category.</p>
                            </div>
                        `
                }

            </div>
        `;

        updateTopNavigation();
        setupMarketplaceEvents(container);
    }

    /* PRODUCT EVENTS */

    function setupMarketplaceEvents(container) {

        container.querySelectorAll("[data-action='view']")
            .forEach(button => {
                button.addEventListener("click", function () {
                    const index = Number(this.dataset.index);
                    const product = marketplaceProducts[index];

                    if (
                        product &&
                        typeof openProductDetails === "function"
                    ) {
                        openProductDetails(product);
                    }
                });
            });

        container.querySelectorAll("[data-action='wishlist']")
            .forEach(button => {
                button.addEventListener("click", function () {
                    const index = Number(this.dataset.index);
                    const product = marketplaceProducts[index];

                    if (!product) return;
                    if (typeof addToWishlist !== "function") return;

                    const productId = product.id ??
                        product.product_id ??
                        product.sku ??
                        getName(product);

                    if (
                        typeof isInWishlist === "function" &&
                        isInWishlist(productId)
                    ) {
                        if (typeof removeFromWishlist === "function") {
                            removeFromWishlist(productId);
                        }
                    } else {
                        addToWishlist(product);
                    }

                    renderMarketplace();
                });
            });
    }

    /* LOAD PRODUCT CATALOGUE */

    async function loadMarketplaceProducts() {
        const container = document.getElementById("productsPageContent");

        if (!container) return;

        container.innerHTML = `
            <div class="marketplace-loading">
                <i class="fa-solid fa-spinner fa-spin"></i>
                Loading your products...
            </div>
        `;

        try {
            const response = await fetch(PRODUCT_DATA_URL);

            if (!response.ok) {
                throw new Error(
                    `Product catalogue returned ${response.status}`
                );
            }

            const data = await response.json();

            marketplaceProducts = Array.isArray(data)
                ? data
                : Array.isArray(data.products)
                    ? data.products
                    : [];

            if (!marketplaceProducts.length) {
                throw new Error("The product catalogue is empty.");
            }

            window.marketplaceProducts = marketplaceProducts;

            renderMarketplace();

        } catch (error) {
            console.error("Marketplace loading error:", error);

            container.innerHTML = `
                <div class="marketplace-empty">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <h3>Unable to load products</h3>
                    <p>
                        Check that products.json exists inside
                        backend/database and that Live Server is
                        serving the project root.
                    </p>
                </div>
            `;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        setupTopNavigation();
        loadMarketplaceProducts();
    });

    window.renderMarketplace = renderMarketplace;
    window.loadMarketplaceProducts = loadMarketplaceProducts;

})();
