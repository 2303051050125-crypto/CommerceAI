
const BACKEND_URL = "http://127.0.0.1:5000";
const MONTHLY_BUDGET = 15000;

window.productCatalog = [];
window.currentProduct = null;
window.shoppingContext = null;
window.lastRecommendedProducts = [];

/* =====================================================
   DOM AND GENERAL HELPERS
===================================================== */

function $(id) {
    return document.getElementById(id);
}

function escapeHTML(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatCurrency(value) {
    return "₹" + (Number(value) || 0).toLocaleString("en-IN");
}

function getProductEmoji(category = "") {
    const value = String(category).toLowerCase();

    if (value.includes("laptop") || value.includes("computer")) return "💻";
    if (value.includes("phone") || value.includes("mobile")) return "📱";
    if (value.includes("tablet")) return "📱";
    if (value.includes("headphone") || value.includes("audio")) return "🎧";
    if (value.includes("watch")) return "⌚";
    if (value.includes("camera")) return "📷";
    if (value.includes("tv") || value.includes("television")) return "📺";
    if (value.includes("gaming") || value.includes("console")) return "🎮";
    if (value.includes("shoe")) return "👟";
    if (value.includes("cloth") || value.includes("fashion")) return "👕";
    if (value.includes("book")) return "📚";
    if (value.includes("furniture")) return "🪑";
    if (value.includes("home")) return "🏠";

    return "🛍️";
}

/* =====================================================
   LOCAL PRODUCT IMAGE SYSTEM
===================================================== */

const PRODUCT_IMAGES = {
    "asus vivobook 15":
        "assets/products/asus-vivobook-15.png",

    "lenovo ideapad slim 5":
        "assets/products/lenovo-ideapad-slim-5.png",

    "hp pavilion 15":
        "assets/products/hp-pavilion-15.jpg",

    "acer aspire 7":
        "assets/products/acer-aspire-7.png",

    "dell inspiron 15":
        "assets/products/dell-inspiron-15.png",

    "sony wh-1000xm6":
        "assets/products/sony-wh1000xm6.jpg",

    "samsung galaxy s25":
        "assets/products/samsung-galaxy-s25.jpg"
};

function normalizeProductName(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}

function getProductImagePath(product) {
    if (!product) return null;

    const name = normalizeProductName(
        product.name ??
        product.product_name ??
        product.title ??
        ""
    );

    const brand = normalizeProductName(product.brand ?? "");

    const fullName = `${brand} ${name}`.trim();

    for (const [productName, imagePath] of Object.entries(PRODUCT_IMAGES)) {
        const normalizedKey = normalizeProductName(productName);

        if (
            name === normalizedKey ||
            fullName.includes(normalizedKey) ||
            name.includes(normalizedKey)
        ) {
            return imagePath;
        }
    }

    return null;
}

function getProductImageHTML(product, containerClass = "product-image-large") {
    const imagePath = getProductImagePath(product);

    const category = product?.category ?? "";
    const fallbackEmoji = getProductEmoji(category);

    if (!imagePath) {
        return `
            <div class="${containerClass} product-photo product-photo-fallback">
                <span>${fallbackEmoji}</span>
            </div>
        `;
    }

    return `
        <div class="${containerClass} product-photo">

            <img
                src="${imagePath}"
                alt="${escapeHTML(product.name ?? product.product_name ?? "Product")}"
                loading="lazy"
                onerror="
                    this.style.display='none';
                    this.nextElementSibling.style.display='flex';
                "
            >

            <span
                class="product-image-fallback"
                style="display:none;"
            >
                ${fallbackEmoji}
            </span>

        </div>
    `;
}

/* =====================================================
   WISHLIST
===================================================== */

function getProductId(product) {
    if (!product) return null;

    return (
        product.id ??
        product.product_id ??
        product.sku ??
        product.name ??
        product.product_name ??
        null
    );
}

function getWishlist() {
    try {
        const wishlist = JSON.parse(
            localStorage.getItem("commerceAIWishlist")
        );

        return Array.isArray(wishlist) ? wishlist : [];

    } catch {
        return [];
    }
}

function saveWishlist(wishlist) {
    localStorage.setItem(
        "commerceAIWishlist",
        JSON.stringify(wishlist)
    );
}

function isInWishlist(productId) {
    if (productId === null || productId === undefined) {
        return false;
    }

    return getWishlist().some(item => {
        return String(getProductId(item)) === String(productId);
    });
}

function addToWishlist(product) {
    if (!product) return;

    const productId = getProductId(product);

    if (productId === null) {
        alert("Unable to add this product to your wishlist.");
        return;
    }

    const wishlist = getWishlist();

    const alreadyExists = wishlist.some(item => {
        return String(getProductId(item)) === String(productId);
    });

    if (alreadyExists) {
        alert("This product is already in your wishlist.");
        updateWishlistButton(productId);
        return;
    }

    wishlist.push(product);

    saveWishlist(wishlist);

    renderWishlist();
    updateWishlistButton(productId);

    alert(
        `${product.name || product.product_name || "Product"} added to your wishlist.`
    );
}

function removeFromWishlist(productId) {
    const wishlist = getWishlist().filter(item => {
        return String(getProductId(item)) !== String(productId);
    });

    saveWishlist(wishlist);

    renderWishlist();
    updateWishlistButton(productId);
}

function updateWishlistButton(productId) {
    const button = document.querySelector(
        ".wishlist-product-button"
    );

    if (!button) return;

    if (isInWishlist(productId)) {
        button.innerHTML =
            '<i class="fas fa-heart"></i> In Wishlist';
    } else {
        button.innerHTML =
            '<i class="far fa-heart"></i> Add to Wishlist';
    }
}

/* Render saved products on the Wishlist page */

function renderWishlist() {
    const container = $("wishlistPageContent");

    if (!container) {
        console.warn(
            "Wishlist container #wishlistPageContent was not found."
        );
        return;
    }

    const wishlist = getWishlist();

    if (wishlist.length === 0) {
        container.innerHTML = `
            <div class="empty-state wishlist-empty-state">

                <div class="wishlist-empty-icon">
                    <i class="far fa-heart"></i>
                </div>

                <h3>Your wishlist is empty</h3>

                <p>
                    Save products you like and they will appear here.
                </p>

                <button
                    class="product-button"
                    id="wishlistBrowseButton"
                    type="button"
                >
                    <i class="fas fa-shopping-bag"></i>
                    Explore Products
                </button>

            </div>
        `;

        const browseButton = $("wishlistBrowseButton");

        if (browseButton) {
            browseButton.addEventListener("click", () => {
                navigateToPage("products");
            });
        }

        return;
    }

    container.innerHTML = `
        <div class="wishlist-summary">
            <p>
                <strong>${wishlist.length}</strong>
                saved product${wishlist.length === 1 ? "" : "s"}
            </p>
        </div>

        <div class="product-results wishlist-grid">

            ${wishlist.map((product, index) => {

                const name =
                    product.name ??
                    product.product_name ??
                    "Product";

                const brand =
                    product.brand ??
                    "Brand";

                const category =
                    product.category ??
                    "general";

                const price =
                    product.price ??
                    0;

                const rating =
                    product.rating ??
                    "N/A";

                const features =
                    getFeaturesText(product);

                return `
                    <div class="product-card wishlist-card">

                        ${getProductImageHTML(product)}

                        <h3>
                            ${escapeHTML(name)}
                        </h3>

                        <div class="product-brand">
                            ${escapeHTML(brand)}
                        </div>

                        <div class="rating">
                            ⭐ ${escapeHTML(rating)}
                        </div>

                        <div class="product-features">
                            ${escapeHTML(features)}
                        </div>

                        <div class="product-bottom">

                            <div class="product-price">
                                ${formatCurrency(price)}
                            </div>

                        </div>

                        <div class="wishlist-card-actions">

                            <button
                                class="product-button wishlist-view-button"
                                type="button"
                                data-index="${index}"
                            >
                                View Product
                            </button>

                            <button
                                class="wishlist-remove-button"
                                type="button"
                                data-index="${index}"
                                title="Remove from wishlist"
                            >
                                <i class="fas fa-trash-alt"></i>
                                Remove
                            </button>

                        </div>

                    </div>
                `;
            }).join("")}

        </div>
    `;

    container
        .querySelectorAll(".wishlist-view-button")
        .forEach(button => {

            button.addEventListener("click", function() {

                const index = Number(this.dataset.index);

                viewWishlistProduct(index);

            });

        });

    container
        .querySelectorAll(".wishlist-remove-button")
        .forEach(button => {

            button.addEventListener("click", function() {

                const index = Number(this.dataset.index);

                const currentWishlist = getWishlist();
                const product = currentWishlist[index];

                if (!product) return;

                const confirmed = confirm(
                    `Remove ${product.name || product.product_name || "this product"} from your wishlist?`
                );

                if (!confirmed) return;

                removeFromWishlist(getProductId(product));

            });

        });
}

function viewWishlistProduct(index) {
    const wishlist = getWishlist();
    const product = wishlist[index];

    if (!product) return;

    openProductDetails(product);
}

/* =====================================================
   SIDEBAR
===================================================== */

function toggleSidebar() {
    const sidebar = document.querySelector(".sidebar");

    if (sidebar) {
        sidebar.classList.toggle("mobile-open");
    }
}

function closeMobileSidebar() {
    const sidebar = document.querySelector(".sidebar");

    if (sidebar) {
        sidebar.classList.remove("mobile-open");
    }
}

/* =====================================================
   SPA NAVIGATION CONTROLLER
===================================================== */

function navigateToPage(pageName) {
    const validPages = [
        "dashboard",
        "products",
        "wishlist",
        "alerts",
        "budget",
        "purchases",
        "analytics",
        "profile",
        "settings"
    ];

    const page = validPages.includes(pageName)
        ? pageName
        : "dashboard";

    const targetHash = `#${page}`;

    if (window.location.hash !== targetHash) {
        window.location.hash = targetHash;
    } else {
        showPage(page);
    }
}

function showPage(pageName) {
    const validPages = [
        "dashboard",
        "products",
        "wishlist",
        "alerts",
        "budget",
        "purchases",
        "analytics",
        "profile",
        "settings"
    ];

    const page = validPages.includes(pageName)
        ? pageName
        : "dashboard";

    document.querySelectorAll("[data-page-section]").forEach(section => {

        const isActive =
            section.dataset.pageSection === page;

        section.hidden = !isActive;
        section.style.display = isActive ? "" : "none";
        section.classList.toggle("active", isActive);

    });

    document.querySelectorAll(".nav-link[data-page]").forEach(link => {

        const isActive =
            link.dataset.page === page;

        link.classList.toggle("active", isActive);

        if (isActive) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }

    });

    closeMobileSidebar();

    window.scrollTo({
        top: 0,
        behavior: "auto"
    });

   if (page === "wishlist") {
    renderWishlist();
   }

   if (page === "purchases") {
    loadPurchaseHistory();
   }
}

function setupNavigation() {

    document.querySelectorAll(".nav-link[data-page]").forEach(link => {

        link.addEventListener("click", function(event) {

            event.preventDefault();

            const page = this.dataset.page;

            navigateToPage(page);

        });

    });

    window.addEventListener("hashchange", function() {

        const page =
            window.location.hash.replace("#", "") ||
            "dashboard";

        showPage(page);

    });

    const initialPage =
        window.location.hash.replace("#", "") ||
        "dashboard";

    showPage(initialPage);
}

/* =====================================================
   AI ASSISTANT
===================================================== */

// Open AI Assistant popup
function openAssistant() {
    const modal = $("assistantModal");

    if (modal) {
        modal.classList.add("show");
        return;
    }

    // Fallback if the popup does not exist
    navigateToPage("dashboard");

    const chatInput = document.querySelector(".chat-input input");

    if (chatInput) {
        chatInput.focus();
    }
}

// Close AI Assistant popup
function closeAssistant() {
    const modal = $("assistantModal");

    if (modal) {
        modal.classList.remove("show");
    }
}

// Connect AI Assistant quick-action buttons
function setupAssistantQuickActions() {
    const buttons = document.querySelectorAll(
        "#assistantModal .quick-actions button"
    );

    const prompts = {
        "find products":
            "Help me find the best products for my needs.",

        "compare prices":
            "Compare the available products and their prices.",

        "find deals":
            "Find the best deals among available products.",

        "check my budget":
            "Help me review my shopping budget."
    };

    buttons.forEach(button => {
        button.addEventListener("click", function () {
            const action = this.textContent.trim().toLowerCase();
            const message = prompts[action];

            if (!message) {
                console.warn("Unknown AI quick action:", action);
                return;
            }

            closeAssistant();
            navigateToPage("dashboard");

            const chatInput = document.querySelector(
                ".chat-input input"
            );

            if (!chatInput) {
                console.error("AI chat input not found.");
                return;
            }

            chatInput.value = message;
            sendMessage();
        });
    });
}

/* =====================================================
   CHAT
===================================================== */

async function sendMessage() {
    const input =
        document.querySelector(".chat-input input");

    if (!input) return;

    const message =
        input.value.trim();

    if (!message) return;

    addUserMessage(message);

    input.value = "";

    const typingId = showTyping();

    let data;

    try {

        const response = await fetch(
            `${BACKEND_URL}/api/chat`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    message: message,

                    previous_context:
                        window.shoppingContext || null,

                    previous_products:
                        window.lastRecommendedProducts || []

                })
            }
        );

        if (!response.ok) {
            throw new Error(
                `Backend returned ${response.status}`
            );
        }

        data = await response.json();

        removeTyping(typingId);

    } catch (error) {

        console.error(
            "Backend request error:",
            error
        );

        removeTyping(typingId);

        addAIMessage(
            "⚠️ I couldn't connect to the backend. Please make sure Flask is running on port 5000.",
            true
        );

        return;
    }

    window.shoppingContext = {

        category:
            data.category ??
            window.shoppingContext?.category ??
            null,

        budget:
            data.budget ??
            window.shoppingContext?.budget ??
            null,

        purpose:
            data.purpose ??
            window.shoppingContext?.purpose ??
            null,

        preferences:
            Array.isArray(data.preferences)
                ? data.preferences
                : (
                    window.shoppingContext?.preferences ||
                    []
                )

    };

    try {

        const aiText =
            data.response ||
            data.message ||
            "I received your request.";

        addAIMessage(aiText);

        if (
            Array.isArray(data.products) &&
            data.products.length > 0
        ) {

            addProductResults(data.products);

        }

    } catch (error) {

        console.error(
            "Frontend rendering error:",
            error
        );

        addAIMessage(
            "⚠️ I received the recommendation, but there was a problem displaying the product results.",
            true
        );

    }
}

function handleEnter(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
}

function sendSuggestion(text) {
    const input = document.querySelector(".chat-input input");

    if (!input) return;

    input.value = text;
    sendMessage();
}

function addUserMessage(text) {
    const chatArea = document.querySelector(".chat-area");

    if (!chatArea) return;

    const message = document.createElement("div");

    message.className = "message user-message";

    message.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-user"></i>
        </div>

        <div class="message-content">
            <p>${escapeHTML(text)}</p>
        </div>
    `;

    chatArea.appendChild(message);
    scrollChatToBottom();
}

function addAIMessage(text, isError = false) {
    const chatArea = document.querySelector(".chat-area");

    if (!chatArea) return;

    const message = document.createElement("div");

    message.className = "message";

    message.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>

        <div class="message-content">
            <p class="${isError ? "error-message" : ""}">
                ${escapeHTML(text)}
            </p>
        </div>
    `;

    chatArea.appendChild(message);
    scrollChatToBottom();
}

function showTyping() {
    const chatArea = document.querySelector(".chat-area");

    if (!chatArea) return null;

    const id = `typing-${Date.now()}`;

    const message = document.createElement("div");

    message.className = "message";
    message.id = id;

    message.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>

        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    chatArea.appendChild(message);
    scrollChatToBottom();

    return id;
}

function removeTyping(id) {
    if (!id) return;

    const element = document.getElementById(id);

    if (element) {
        element.remove();
    }
}

function scrollChatToBottom() {
    const chatArea = document.querySelector(".chat-area");

    if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight;
    }
}

/* =====================================================
   PRODUCT RESULTS
===================================================== */

function addProductResults(products) {
    if (!Array.isArray(products) || products.length === 0) {
        return;
    }

    window.productCatalog = products;
    window.lastRecommendedProducts = products;

    const chatArea = document.querySelector(".chat-area");

    if (!chatArea) return;

    const oldResults =
        chatArea.querySelector(".product-results");

    if (oldResults) {
        oldResults.remove();
    }

    const results = document.createElement("div");

    results.className = "product-results";

    results.innerHTML = products.map((product, index) => {

        const name =
            product.name ??
            product.product_name ??
            "Product";

        const brand =
            product.brand ??
            "Brand";

        const category =
            product.category ??
            "general";

        const price =
            product.price ??
            0;

        const rating =
            product.rating ??
            "N/A";

        const reviews =
            product.reviews ??
            product.review_count ??
            0;

        const features =
            getFeaturesText(product);

        const matchScore =
            product.match_score;

        const matchScoreHTML =
            matchScore !== undefined &&
            matchScore !== null
                ? `
                    <div class="ai-match-score">
                        🎯 ${escapeHTML(matchScore)}% Match
                    </div>
                  `
                : "";

        return `
            <div class="product-card">

                ${getProductImageHTML(product)}

                <h3>
                    ${escapeHTML(name)}
                </h3>

                <div class="product-brand">
                    ${escapeHTML(brand)}
                </div>

                ${matchScoreHTML}

                <div class="rating">
                    ⭐ ${escapeHTML(rating)}
                    ${reviews
                        ? `(${escapeHTML(reviews)} reviews)`
                        : ""
                    }
                </div>

                <div class="product-features">
                    ${escapeHTML(features)}
                </div>

                <div class="product-bottom">

                    <div class="product-price">
                        ${formatCurrency(price)}
                    </div>

                    <button
                        class="product-button"
                        onclick="selectProduct(${index})"
                    >
                        View Product
                    </button>

                </div>

            </div>
        `;
    }).join("");

    chatArea.appendChild(results);

    scrollChatToBottom();
}

function getFeaturesText(product) {
    if (Array.isArray(product.features)) {
        return product.features.join(" • ");
    }

    if (typeof product.features === "string") {
        return product.features;
    }

    if (product.description) {
        return product.description;
    }

    const values = [];

    if (product.processor) {
        values.push(product.processor);
    }

    if (product.ram) {
        values.push(product.ram);
    }

    if (product.storage) {
        values.push(product.storage);
    }

    if (product.display) {
        values.push(product.display);
    }

    return values.join(" • ") || "Product details available";
}

/* =====================================================
   PRODUCT DETAILS
===================================================== */

function selectProduct(index) {
    const product =
        window.productCatalog[index];

    if (!product) return;

    openProductDetails(product);
}

function openProductDetails(product) {
    if (!product) return;

    window.currentProduct = product;

    let modal = $("productModal");

    if (!modal) {
        modal = document.createElement("div");

        modal.id = "productModal";
        modal.className = "modal";

        modal.innerHTML = `
            <div class="modal-content">

                <div class="modal-header">
                    <h2>Product Details</h2>

                    <button
                        class="close-modal"
                        onclick="closeProductDetails()"
                    >
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div id="productDetailContent"></div>

            </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener(
            "click",
            handleProductOverlayClick
        );
    }

    const id = getProductId(product);

    const name =
        product.name ??
        product.product_name ??
        "Product";

    const brand =
        product.brand ??
        "Brand";

    const category =
        product.category ??
        "general";

    const price =
        product.price ??
        0;

    const rating =
        product.rating ??
        "N/A";

    const reviews =
        product.reviews ??
        product.review_count ??
        0;

    const features =
        getFeatureArray(product);

    const detail =
        $("productDetailContent");

    const matchScore =
        product.match_score;

    const breakdown =
        product.match_breakdown;

    let aiRecommendationHTML = "";

    if (
        matchScore !== undefined &&
        matchScore !== null &&
        breakdown
    ) {

        const categoryScore =
            breakdown.category?.score ?? 0;

        const categoryMaximum =
            breakdown.category?.maximum ?? 25;

        const budgetScore =
            breakdown.budget?.score ?? 0;

        const budgetMaximum =
            breakdown.budget?.maximum ?? 30;

        const purposeScore =
            breakdown.purpose?.score ?? 0;

        const purposeMaximum =
            breakdown.purpose?.maximum ?? 20;

        const preferenceScore =
            breakdown.preferences?.score ?? 0;

        const preferenceMaximum =
            breakdown.preferences?.maximum ?? 15;

        const ratingScore =
            breakdown.rating?.score ?? 0;

        const ratingMaximum =
            breakdown.rating?.maximum ?? 5;

        const reviewScore =
            breakdown.reviews?.score ?? 0;

        const reviewMaximum =
            breakdown.reviews?.maximum ?? 5;

        aiRecommendationHTML = `

            <div class="ai-recommendation">

                <div class="ai-recommendation-header">

                    <div>

                        <h3>
                            <i class="fas fa-robot"></i>
                            AI Recommendation Analysis
                        </h3>

                        <p>
                            Based on your requirements
                        </p>

                    </div>

                    <div class="ai-match-badge">
                        🎯
                        ${escapeHTML(matchScore)}%
                        Match
                    </div>

                </div>

                <div class="ai-score-breakdown">

                    <div class="score-row">
                        <span>Category</span>
                        <strong>${categoryScore} / ${categoryMaximum}</strong>
                    </div>

                    <div class="score-row">
                        <span>Budget</span>
                        <strong>${budgetScore} / ${budgetMaximum}</strong>
                    </div>

                    <div class="score-row">
                        <span>Purpose</span>
                        <strong>${purposeScore} / ${purposeMaximum}</strong>
                    </div>

                    <div class="score-row">
                        <span>Preferences</span>
                        <strong>${preferenceScore} / ${preferenceMaximum}</strong>
                    </div>

                    <div class="score-row">
                        <span>Rating</span>
                        <strong>${ratingScore} / ${ratingMaximum}</strong>
                    </div>

                    <div class="score-row">
                        <span>Reviews</span>
                        <strong>${reviewScore} / ${reviewMaximum}</strong>
                    </div>

                </div>

            </div>
        `;
    }

    detail.innerHTML = `

        <div class="product-detail">

            <div class="product-detail-top">

                ${getProductImageHTML(product, "product-detail-image")}

                <div class="product-detail-info">

                    <h2>${escapeHTML(name)}</h2>

                    <div class="brand">
                        ${escapeHTML(brand)}
                    </div>

                    <div class="detail-rating">
                        ⭐
                        ${escapeHTML(rating)}
                        ${
                            reviews
                                ? `(${escapeHTML(reviews)} reviews)`
                                : ""
                        }
                    </div>

                    <div class="detail-price">
                        ${formatCurrency(price)}
                    </div>

                    <ul class="detail-features">

                        ${
                            features.map(
                                feature =>
                                    `<li>${escapeHTML(feature)}</li>`
                            ).join("")
                        }

                    </ul>

                </div>

            </div>

            ${aiRecommendationHTML}

            <div class="modal-actions">

                <button
                    class="buy-button"
                    onclick="buyProduct()"
                >
                    <i class="fas fa-shopping-cart"></i>
                    Buy Product
                </button>

                <button
                    class="wishlist-product-button"
                    onclick="toggleCurrentWishlist()"
                >
                    <i class="far fa-heart"></i>
                    Add to Wishlist
                </button>

            </div>

        </div>
    `;

    modal.classList.add("show");

    updateWishlistButton(id);
}

function getFeatureArray(product) {
    if (Array.isArray(product.features)) {
        return product.features;
    }

    if (typeof product.features === "string") {
        return product.features
            .split("•")
            .map(item => item.trim())
            .filter(Boolean);
    }

    const features = [];

    if (product.processor) {
        features.push(product.processor);
    }

    if (product.ram) {
        features.push(product.ram);
    }

    if (product.storage) {
        features.push(product.storage);
    }

    if (product.display) {
        features.push(product.display);
    }

    if (product.description) {
        features.push(product.description);
    }

    return features.length
        ? features
        : ["Product details available"];
}

function closeProductDetails() {
    const modal = $("productModal");

    if (modal) {
        modal.classList.remove("show");
    }

    window.currentProduct = null;
}

function handleProductOverlayClick(event) {
    if (event.target.classList.contains("modal")) {
        closeProductDetails();
    }
}

function toggleCurrentWishlist() {
    const product =
        window.currentProduct;

    if (!product) return;

    const id = getProductId(product);

    if (isInWishlist(id)) {

        removeFromWishlist(id);

        alert("Removed from wishlist.");

    } else {

        addToWishlist(product);

    }

    updateWishlistButton(id);
}

/* =====================================================
   BUY PRODUCT
===================================================== */

async function buyProduct() {
    const product =
        window.currentProduct;

    if (!product) {
        alert("Please select a product first.");
        return;
    }

    const productId =
        product.id ??
        product.product_id;

    const productName =
        product.name ??
        product.product_name ??
        "Product";

    const price =
        Number(product.price) || 0;

    const confirmed = confirm(
        `Buy ${productName} for ${formatCurrency(price)}?`
    );

    if (!confirmed) return;

    try {
        const response = await fetch(
            `${BACKEND_URL}/api/purchase`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    product_id: productId,
                    product_name: productName,
                    price: price,
                    quantity: 1
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.message ||
                data.error ||
                "Purchase failed"
            );
        }

        alert(
            data.message ||
            "Purchase completed successfully!"
        );

        closeProductDetails();

        await loadPurchaseHistory();
        await loadDashboardStats();

    } catch (error) {
        console.error("Purchase error:", error);

        alert(
            "❌ Purchase failed. Please make sure the Flask backend is running."
        );
    }
}

/* =====================================================
   SEARCH
===================================================== */

function setupSearch() {
    const searchInput =
        document.querySelector(".search-box input");

    if (!searchInput) return;

    searchInput.addEventListener(
        "input",
        function() {
            const query =
                this.value.trim().toLowerCase();

            document
                .querySelectorAll(".product-card")
                .forEach(card => {
                    const text =
                        card.textContent.toLowerCase();

                    card.style.display =
                        !query ||
                        text.includes(query)
                            ? ""
                            : "none";
                });
        }
    );

    searchInput.addEventListener(
        "keydown",
        event => {
            if (event.key === "Enter") {
                const value =
                    searchInput.value.trim();

                if (value) {
                    const chatInput =
                        document.querySelector(
                            ".chat-input input"
                        );

                    if (chatInput) {
                        chatInput.value =
                            `Show me ${value}`;

                        sendMessage();

                        searchInput.value = "";
                    }
                }
            }
        }
    );
}

/* =====================================================
   PRICE ALERT
===================================================== */

function addPriceAlert(productName = "this product") {
    alert(
        `🔔 Price alert created for ${productName}.`
    );
}


/* =====================================================
   PURCHASE CATEGORY CATALOGUE
===================================================== */

let purchaseCataloguePromise = null;

async function getPurchaseCatalogue() {
    // Reuse the marketplace catalogue if already loaded
    if (
        Array.isArray(window.marketplaceProducts) &&
        window.marketplaceProducts.length > 0
    ) {
        return window.marketplaceProducts;
    }

    // Avoid making repeated requests
    if (!purchaseCataloguePromise) {
        purchaseCataloguePromise = fetch(
            "../backend/database/products.json"
        )
            .then(response => {
                if (!response.ok) {
                    throw new Error(
                        "Unable to load product catalogue"
                    );
                }

                return response.json();
            })
            .then(data => {
                const catalogue = Array.isArray(data)
                    ? data
                    : Array.isArray(data.products)
                        ? data.products
                        : [];

                window.marketplaceProducts = catalogue;

                return catalogue;
            })
            .catch(error => {
                console.error(
                    "Purchase catalogue error:",
                    error
                );

                purchaseCataloguePromise = null;

                return [];
            });
    }

    return purchaseCataloguePromise;
}

/* =====================================================
   PURCHASE HISTORY
===================================================== */


async function loadPurchaseHistory() {
    const body = $("purchaseHistoryBody");

    if (!body) return;

    try {
        const response = await fetch(
            `${BACKEND_URL}/api/purchases`
        );

        if (!response.ok) {
            throw new Error("Unable to load purchases");
        }

        const data = await response.json();
        await getPurchaseCatalogue();
        const purchases = Array.isArray(data)
            ? data
            : (data.purchases || []);
        renderPurchasesPage(purchases);
        body.innerHTML = "";

        if (!purchases.length) {
            body.innerHTML = `
                <tr>
                    <td colspan="6">
                        <div class="empty-state">
                            No purchases found.
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        purchases.slice().reverse().forEach(purchase => {
            const row = document.createElement("tr");

            const productName =
                purchase.product_name ||
                purchase.name ||
                "Product";

            const category = getPurchaseCategory(purchase);

            const total =
                Number(purchase.total) ||
                (Number(purchase.price) || 0) *
                (Number(purchase.quantity) || 1);

            const status = purchase.status || "Purchased";

            row.innerHTML = `
                <td>
                    <div class="table-product">
                        <span class="product-image">
                            ${getProductEmoji(category)}
                        </span>
                        <div>
                            <strong>${escapeHTML(productName)}</strong>
                        </div>
                    </div>
                </td>

                <td>${escapeHTML(category)}</td>

                <td>${formatPurchaseDate(purchase.date)}</td>

                <td>${formatCurrency(total)}</td>

                <td>—</td>

                <td>
                    <span class="status delivered">
                        ${escapeHTML(status)}
                    </span>
                </td>
            `;

            body.appendChild(row);
        });

    } catch (error) {
        console.error("Purchase history error:", error);

        body.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        Unable to load purchase history.
                    </div>
                </td>
            </tr>
        `;
    }
}
function renderPurchasesPage(purchases) {
    const container = $("purchasesPageContent");

    if (!container) return;

    if (!purchases.length) {
        container.innerHTML = `
            <div class="empty-state">
                No purchases found.
            </div>
        `;
        return;
    }

    const rows = purchases.slice().reverse().map(purchase => {
        const productName =
            purchase.product_name ||
            purchase.name ||
            "Product";

        const category = getPurchaseCategory(purchase);

        const total =
            Number(purchase.total) ||
            (Number(purchase.price) || 0) *
            (Number(purchase.quantity) || 1);

        const status = purchase.status || "Purchased";

        return `
            <tr>
                <td>
                    <div class="table-product">
                        <span class="product-image">
                            ${getProductEmoji(category)}
                        </span>
                        <strong>${escapeHTML(productName)}</strong>
                    </div>
                </td>

                <td>${escapeHTML(category)}</td>
                <td>${formatPurchaseDate(purchase.date)}</td>
                <td>${formatCurrency(total)}</td>
                <td>—</td>

                <td>
                    <span class="status delivered">
                        ${escapeHTML(status)}
                    </span>
                </td>
            </tr>
        `;
    }).join("");

    container.innerHTML = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>PRODUCT</th>
                        <th>CATEGORY</th>
                        <th>DATE</th>
                        <th>PRICE</th>
                        <th>AI SAVING</th>
                        <th>STATUS</th>
                    </tr>
                </thead>

                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}



function getPurchaseCategory(purchase) {
    // Prefer category saved in the purchase record
    if (purchase.category) {
        return purchase.category;
    }

    // Search the complete product catalogue
    const catalogue = Array.isArray(window.marketplaceProducts)
        ? window.marketplaceProducts
        : [];

    const product = catalogue.find(item =>
        String(item.id ?? item.product_id) ===
        String(purchase.product_id)
    );

    if (product?.category) {
        return product.category;
    }

    // Fallback for unmatched historical records
    const name = String(
        purchase.product_name ||
        purchase.name ||
        ""
    ).toLowerCase();

    if (name.includes("laptop")) return "laptop";

    if (
        name.includes("iphone") ||
        name.includes("phone")
    ) {
        return "smartphone";
    }

    if (name.includes("headphone")) return "headphones";
    if (name.includes("watch")) return "watch";
    if (name.includes("camera")) return "camera";

    return "product";
}

function formatPurchaseDate(dateValue) {
    if (!dateValue) return "-";

    const date =
        new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return escapeHTML(dateValue);
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}

/* =====================================================
   DASHBOARD STATS
===================================================== */

async function loadDashboardStats() {
    try {
        const response = await fetch(
            `${BACKEND_URL}/api/purchases`
        );

        if (!response.ok) {
            throw new Error(
                "Unable to load dashboard statistics"
            );
        }

        const data =
            await response.json();

        const purchases =
            Array.isArray(data)
                ? data
                : (data.purchases || []);

        const now = new Date();

        const currentMonth =
            now.getMonth();

        const currentYear =
            now.getFullYear();

        const monthlyPurchases =
            purchases.filter(purchase => {
                if (!purchase.date) {
                    return false;
                }

                const date =
                    new Date(purchase.date);

                return (
                    date.getMonth() === currentMonth &&
                    date.getFullYear() === currentYear
                );
            });

        const monthlySpent =
            monthlyPurchases.reduce(
                (sum, purchase) => {
                    const quantity =
                        Number(purchase.quantity) || 1;

                    const total =
                        Number(purchase.total) ||
                        (Number(purchase.price) || 0) * quantity;

                    return sum + total;
                },
                0
            );

        const totalPurchases =
            purchases.length;

        const remaining =
            Math.max(
                MONTHLY_BUDGET - monthlySpent,
                0
            );

        const progress =
            Math.min(
                (monthlySpent / MONTHLY_BUDGET) * 100,
                100
            );

        const monthlyBudgetElement =
            $("monthlyBudget");

        const budgetSummaryElement =
            $("budgetSummary");

        const budgetProgressElement =
            $("budgetProgress");

        const totalPurchasesElement =
            $("totalPurchases");

        const monthlyPurchasesElement =
            $("monthlyPurchases");

        if (monthlyBudgetElement) {
            monthlyBudgetElement.textContent =
                formatCurrency(MONTHLY_BUDGET);
        }

        if (budgetSummaryElement) {
            budgetSummaryElement.textContent =
                `${formatCurrency(monthlySpent)} spent · ${formatCurrency(remaining)} remaining`;
        }

        if (budgetProgressElement) {
            budgetProgressElement.style.width =
                `${progress}%`;
        }

        if (totalPurchasesElement) {
            totalPurchasesElement.textContent =
                totalPurchases;
        }

        if (monthlyPurchasesElement) {
            monthlyPurchasesElement.textContent =
                `${monthlyPurchases.length} purchase${monthlyPurchases.length === 1 ? "" : "s"} this month`;
        }

    } catch (error) {
        console.error(
            "Dashboard statistics error:",
            error
        );
    }
}

/* =====================================================
   QUICK ACTIONS
===================================================== */

function setupQuickActions() {
    document
        .querySelectorAll(".view-all")
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    const target =
                        button.closest(".panel");

                    if (target) {
                        target.scrollIntoView({
                            behavior: "smooth",
                            block: "center"
                        });
                    }
                }
            );
        });

    document
        .querySelectorAll(".add-alert")
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    const alertElement =
                        button.closest(".alert");

                    const name =
                        alertElement
                            ?.querySelector(".alert-info h3")
                            ?.textContent ||
                        "this product";

                    addPriceAlert(name.trim());
                }
            );
        });
}

/* =====================================================
   NOTIFICATIONS
===================================================== */

function setupNotifications() {
    const button =
        document.querySelector(".icon-button");

    if (!button) return;

    button.addEventListener(
        "click",
        () => {
            alert(
                "🔔 You have 3 active price alerts."
            );
        }
    );
}

/* =====================================================
   KEYBOARD
===================================================== */

document.addEventListener(
    "keydown",
    event => {
        if (event.key === "Escape") {
            closeProductDetails();
            closeAssistant();
            closeMobileSidebar();
        }
    }
);

/* =====================================================
   DATE
===================================================== */

function updateWelcomeDate() {
    const element =
        document.querySelector(".small-text");

    if (!element) return;

    const date = new Date();

    element.textContent =
        date.toLocaleDateString(
            "en-IN",
            {
                weekday: "long",
                month: "long",
                day: "numeric"
            }
        );
}

/* =====================================================
   INITIALIZATION
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        setupNavigation();
        setupSearch();
        setupQuickActions();
        setupNotifications();
        setupAssistantQuickActions();
        
        
        updateWelcomeDate();

        renderWishlist();

        const chatInput =
            document.querySelector(".chat-input input");

        if (chatInput) {
            chatInput.addEventListener(
                "keydown",
                handleEnter
            );
        }

        const mobileMenu =
            document.querySelector(".mobile-menu");

        if (mobileMenu) {
            mobileMenu.addEventListener(
                "click",
                toggleSidebar
            );
        }

        await Promise.all([
            loadPurchaseHistory(),
            loadDashboardStats()
        ]);
    }
);

/* =====================================================
   GLOBAL FUNCTIONS
===================================================== */

window.sendMessage = sendMessage;
window.handleEnter = handleEnter;
window.sendSuggestion = sendSuggestion;
window.openAssistant = openAssistant;
window.closeAssistant = closeAssistant;

window.selectProduct = selectProduct;
window.closeProductDetails = closeProductDetails;
window.buyProduct = buyProduct;

window.addToWishlist = addToWishlist;
window.removeFromWishlist = removeFromWishlist;
window.toggleCurrentWishlist = toggleCurrentWishlist;
window.renderWishlist = renderWishlist;
window.viewWishlistProduct = viewWishlistProduct;

window.addPriceAlert = addPriceAlert;
window.toggleSidebar = toggleSidebar;
window.loadPurchaseHistory = loadPurchaseHistory;
window.loadDashboardStats = loadDashboardStats;
window.navigateToPage = navigateToPage;
