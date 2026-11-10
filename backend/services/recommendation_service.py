
"""
AI Product Recommendation Engine
"""

import re


# =========================================================
# CATEGORY MATCHING
# =========================================================

def category_matches(product_category, requested_category):

    if not requested_category:
        return True

    product_category = str(product_category).lower().strip()
    requested_category = str(requested_category).lower().strip()

    category_aliases = {
        "headphone": ["headphone", "headphones"],
        "headphones": ["headphone", "headphones"],
        "laptop": ["laptop", "laptops"],
        "laptops": ["laptop", "laptops"],
        "phone": ["phone", "phones", "smartphone", "smartphones"],
        "phones": ["phone", "phones", "smartphone", "smartphones"],
        "smartphone": ["phone", "phones", "smartphone", "smartphones"],
        "smartphones": ["phone", "phones", "smartphone", "smartphones"],
        "tablet": ["tablet", "tablets"],
        "tablets": ["tablet", "tablets"]
    }

    aliases = category_aliases.get(
        requested_category,
        [requested_category]
    )

    return product_category in aliases


# =========================================================
# PRODUCT TEXT NORMALIZATION
# =========================================================

def get_product_text(product):
    """
    Creates searchable text from product information.

    Supports:
    - Legacy product fields
    - Structured specifications
    - Features and tags as lists or strings

    Does not invent missing specifications.
    """

    product_features = product.get("features", [])
    product_tags = product.get("tags", [])

    specifications = product.get(
        "specifications",
        {}
    )

    if not isinstance(specifications, dict):
        specifications = {}

    def normalize_values(value):

        if value is None:
            return ""

        if isinstance(value, dict):

            return " ".join(
                normalize_values(item)
                for item in value.values()
            )

        if isinstance(value, (list, tuple, set)):

            return " ".join(
                normalize_values(item)
                for item in value
            )

        return str(value).lower()

    return " ".join([

        str(product.get("name", "")).lower(),

        str(product.get("description", "")).lower(),

        str(product.get("category", "")).lower(),

        str(product.get("brand", "")).lower(),

        str(product.get("processor", "")).lower(),

        str(product.get("ram", "")).lower(),

        str(product.get("storage", "")).lower(),

        str(product.get("graphics", "")).lower(),

        str(product.get("display", "")).lower(),

        str(product.get("battery", "")).lower(),

        normalize_values(product_features),

        normalize_values(product_tags),

        normalize_values(specifications)

    ])

# =========================================================
# SPECIFICATION REQUIREMENT DETECTION
# =========================================================

def get_hardware_requirement(preference_text):
    """
    Identifies explicit RAM or storage requirements.

    Returns:
        ("ram", required_value) for RAM
        ("storage", required_value_in_gb) for storage
        (None, None) if no recognized requirement exists
    """

    text = (
        str(preference_text)
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )

    # RAM: 16GB RAM, 16 GB memory, RAM 16GB
    ram_match = re.search(
        r"(\d+(?:\.\d+)?)\s*gb\s*(?:ram|memory)",
        text
    )

    if not ram_match:
        ram_match = re.search(
            r"(?:ram|memory)\s*(\d+(?:\.\d+)?)\s*gb",
            text
        )

    if ram_match:
        return "ram", float(ram_match.group(1))

    # Storage: 512GB SSD, 1TB storage, SSD 512GB
    storage_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(gb|tb)\s*"
        r"(?:ssd|storage|hard\s*drive)",
        text
    )

    if not storage_match:
        storage_match = re.search(
            r"(?:ssd|storage|hard\s*drive)\s*"
            r"(\d+(?:\.\d+)?)\s*(gb|tb)",
            text
        )

    if storage_match:
        value = float(storage_match.group(1))
        unit = storage_match.group(2)

        storage_gb = value * 1024 if unit == "tb" else value

        return "storage", storage_gb

    return None, None
# =========================================================
# SPECIFICATION MATCHING
# =========================================================
def specification_matches(preference_text, product_text):
    """
    Checks whether a product satisfies a RAM or storage
    specification.

    Returns False if the product specification cannot
    be verified.
    """

    requirement_type, required_value = get_hardware_requirement(
        preference_text
    )

    if requirement_type is None:
        return False

    normalized_product = (
        str(product_text)
        .lower()
        .replace("-", " ")
        .replace("_", " ")
    )

    if requirement_type == "ram":

        product_ram_values = re.findall(
            r"(\d+(?:\.\d+)?)\s*gb\s*(?:ram|memory)",
            normalized_product
        )

        if not product_ram_values:
            product_ram_values = re.findall(
                r"(?:ram|memory)\s*(\d+(?:\.\d+)?)\s*gb",
                normalized_product
            )

        # Also recognize normalized RAM values such as 16GB.
        if not product_ram_values:
            product_ram_values = re.findall(
                r"(\d+(?:\.\d+)?)\s*gb",
                normalized_product
            )

        if not product_ram_values:
            return False

        return any(
            float(value) >= required_value
            for value in product_ram_values
        )

    if requirement_type == "storage":

        product_storage_matches = re.findall(
            r"(\d+(?:\.\d+)?)\s*(gb|tb)\s*"
            r"(?:ssd|storage|hard\s*drive)",
            normalized_product
        )

        if not product_storage_matches:
            product_storage_matches = re.findall(
                r"(?:ssd|storage|hard\s*drive)\s*"
                r"(\d+(?:\.\d+)?)\s*(gb|tb)",
                normalized_product
            )

        if not product_storage_matches:
            return False

        for value, unit in product_storage_matches:

            product_value = float(value)

            if unit == "tb":
                product_value *= 1024

            if product_value >= required_value:
                return True

        return False

    return False

# =========================================================
# PREFERENCE PRIORITY DETECTION
# =========================================================

def is_high_priority_preference(preference):
    """
    Detects whether the user expressed a preference
    as an important requirement.
    """

    preference_text = str(preference).lower().strip()

    priority_phrases = [
        "at least",
        "minimum",
        "must have",
        "required",
        "essential",
        "need",
        "needs",
        "should have",
        "cannot be below",
        "not less than",
        "no less than"
    ]

    return any(
        phrase in preference_text
        for phrase in priority_phrases
    )


# =========================================================
# STRICT HARDWARE REQUIREMENT CHECK
# =========================================================

def satisfies_strict_hardware_requirements(
    product,
    requirements
):
    """
    Rejects products that fail explicit minimum RAM
    or storage requirements.

    Ordinary preferences are NOT hard-filtered.

    If a strict specification is missing from product
    information, the product is rejected because
    compliance cannot be verified.
    """

    preferences = requirements.get(
        "preferences",
        []
    )

    if isinstance(preferences, str):
        preferences = [preferences]

    product_text = get_product_text(product)

    for preference in preferences:

        if not is_high_priority_preference(preference):
            continue

        requirement_type, required_value = get_hardware_requirement(
            preference
        )

        # Ignore high-priority preferences unrelated
        # to RAM or storage.
        if requirement_type is None:
            continue

        if not specification_matches(
            preference,
            product_text
        ):
            return False

    return True


# =========================================================
# CALCULATE PRODUCT SCORE
# =========================================================

def calculate_product_score(product, requirements):

    category_score = 0
    budget_score = 0
    purpose_score = 0
    preference_score = 0
    rating_score = 0
    review_score = 0

    # =====================================================
    # USER REQUIREMENTS
    # =====================================================

    category = requirements.get("category")
    budget = requirements.get("budget")
    purpose = requirements.get("purpose")
    preferences = requirements.get("preferences", [])

    # =====================================================
    # PRODUCT INFORMATION
    # =====================================================

    product_category = str(
        product.get("category", "")
    ).lower()

    product_text = get_product_text(product)

    # =====================================================
    # 1. CATEGORY SCORE
    # =====================================================

    if category:

        if category_matches(product_category, category):
            category_score = 25

    # =====================================================
    # 2. BUDGET SCORE
    # =====================================================

    price = product.get("price", 0)

    try:
        price = float(price)
    except (ValueError, TypeError):
        price = 0

    if budget:

        try:
            budget = float(budget)
        except (ValueError, TypeError):
            budget = None

    if budget and price:

        if price <= budget:

            percentage_of_budget = price / budget

            if percentage_of_budget >= 0.85:
                budget_score = 30
            elif percentage_of_budget >= 0.70:
                budget_score = 28
            elif percentage_of_budget >= 0.50:
                budget_score = 25
            else:
                budget_score = 22

        else:

            percentage_over = (price - budget) / budget

            if percentage_over <= 0.05:
                budget_score = 20
            elif percentage_over <= 0.10:
                budget_score = 10
            else:
                budget_score = 0

    # =====================================================
    # 3. PURPOSE SCORE
    # =====================================================

    if purpose:

        purpose_text = str(purpose).lower().strip()

        purpose_groups = {

            "programming": [
                "programming", "programmer", "coding",
                "developer", "development"
            ],

            "gaming": [
                "gaming", "gamer", "game"
            ],

            "studying": [
                "studying", "study", "student",
                "college", "education", "learning"
            ],

            "office": [
                "office", "work", "business", "productivity"
            ],

            "photography": [
                "photography", "photograph", "camera", "photo"
            ],

            "music": [
                "music", "audio", "listening"
            ],

            "travel": [
                "travel", "travelling", "traveling"
            ],

            "entertainment": [
                "entertainment", "movies", "movie",
                "streaming", "media"
            ]
        }

        purpose_keywords = []

        for group_name, keywords in purpose_groups.items():

            if (
                group_name in purpose_text
                or any(
                    keyword in purpose_text
                    for keyword in keywords
                )
            ):
                purpose_keywords.extend(keywords)

        if not purpose_keywords:

            purpose_keywords = (
                purpose_text
                .replace(",", " ")
                .split()
            )

        matched_keywords = 0

        for keyword in set(purpose_keywords):

            if len(keyword) <= 2:
                continue

            if keyword in product_text:
                matched_keywords += 1

        if matched_keywords >= 4:
            purpose_score = 20
        elif matched_keywords == 3:
            purpose_score = 15
        elif matched_keywords == 2:
            purpose_score = 10
        elif matched_keywords == 1:
            purpose_score = 8
        else:
            purpose_score = 0

    # =====================================================
    # 4. PRIORITY-AWARE PREFERENCE SCORE
    # =====================================================

    if preferences:

        if isinstance(preferences, str):
            preferences = [preferences]

        preference_aliases = {

            "noise cancellation": [
                "noise cancellation",
                "active noise cancellation",
                "anc"
            ],

            "good battery": [
                "good battery",
                "long battery",
                "long battery life",
                "extended battery",
                "battery life"
            ],

            "long battery": [
                "long battery",
                "long battery life",
                "extended battery",
                "battery life"
            ],

            "lightweight": [
                "lightweight",
                "light weight",
                "light",
                "portable"
            ],

            "portable": [
                "portable",
                "lightweight",
                "light weight",
                "light"
            ],

            "fast processor": [
                "fast processor",
                "powerful processor",
                "high performance processor",
                "high-performance processor",
                "fast cpu",
                "powerful cpu"
            ],

            "powerful processor": [
                "powerful processor",
                "fast processor",
                "high performance processor",
                "high-performance processor",
                "fast cpu",
                "powerful cpu"
            ],

            "good display": [
                "good display",
                "high quality display",
                "high-quality display",
                "high resolution display",
                "high-resolution display",
                "oled",
                "amoled",
                "retina display"
            ],

            "high refresh rate": [
                "high refresh rate",
                "120hz",
                "144hz",
                "165hz",
                "240hz",
                "90hz"
            ],

            "good camera": [
                "good camera",
                "high quality camera",
                "high-quality camera",
                "advanced camera",
                "great camera"
            ],

            "16gb ram": [
                "16gb ram", "16 gb ram",
                "16gb memory", "16 gb memory",
                "ram 16gb", "ram 16 gb"
            ],

            "32gb ram": [
                "32gb ram", "32 gb ram",
                "32gb memory", "32 gb memory",
                "ram 32gb", "ram 32 gb"
            ],

            "8gb ram": [
                "8gb ram", "8 gb ram",
                "8gb memory", "8 gb memory",
                "ram 8gb", "ram 8 gb"
            ],

            "512gb ssd": [
                "512gb ssd", "512 gb ssd",
                "512gb storage", "512 gb storage",
                "ssd 512gb", "ssd 512 gb"
            ],

            "1tb ssd": [
                "1tb ssd", "1 tb ssd",
                "1tb storage", "1 tb storage",
                "ssd 1tb", "ssd 1 tb"
            ],

            "256gb ssd": [
                "256gb ssd", "256 gb ssd",
                "256gb storage", "256 gb storage",
                "ssd 256gb", "ssd 256 gb"
            ],

            "wireless": [
                "wireless", "bluetooth", "wi-fi", "wifi"
            ],

            "premium audio": [
                "premium audio",
                "high quality audio",
                "high-quality audio",
                "enhanced audio",
                "premium sound",
                "high quality sound"
            ]
        }

        # Separate normal and high-priority preferences.

        high_priority_preferences = []
        normal_preferences = []

        for preference in preferences:

            if is_high_priority_preference(preference):
                high_priority_preferences.append(preference)
            else:
                normal_preferences.append(preference)

        # High-priority preferences receive 2x weight.

        preference_weights = {}
        total_weight = 0

        for preference in high_priority_preferences:

            preference_weights[str(preference)] = 2
            total_weight += 2

        for preference in normal_preferences:

            preference_weights[str(preference)] = 1
            total_weight += 1

        matched_weight = 0

        for preference in preferences:

            preference_text = str(preference).lower().strip()

            if not preference_text:
                continue

            normalized_preference = (
                preference_text
                .replace("-", " ")
                .replace("_", " ")
                .strip()
            )

            normalized_product_text = (
                product_text
                .replace("-", " ")
                .replace("_", " ")
            )

            # Remove priority wording before alias matching.

            matching_preference = normalized_preference

            priority_prefixes = [
                "at least ",
                "minimum ",
                "must have ",
                "required ",
                "essential ",
                "need ",
                "needs ",
                "should have "
            ]

            for prefix in priority_prefixes:

                if matching_preference.startswith(prefix):

                    matching_preference = (
                        matching_preference[len(prefix):]
                    )

                    break

            # Specification matching.

            matched = specification_matches(
                normalized_preference,
                normalized_product_text
            )

            # Semantic alias matching.

            if not matched:

                aliases = preference_aliases.get(
                    matching_preference,
                    [matching_preference]
                )

                for alias in aliases:

                    normalized_alias = (
                        str(alias)
                        .lower()
                        .replace("-", " ")
                        .replace("_", " ")
                        .strip()
                    )

                    if normalized_alias in normalized_product_text:

                        matched = True
                        break

            if matched:

                matched_weight += preference_weights.get(
                    str(preference),
                    1
                )

        if total_weight > 0:

            preference_score = round(
                (matched_weight / total_weight) * 15,
                2
            )

        else:
            preference_score = 0

    # =====================================================
    # 5. RATING SCORE
    # =====================================================

    rating = product.get("rating", 0)

    try:
        rating = float(rating)
    except (ValueError, TypeError):
        rating = 0

    rating_score = min(5, rating)

    # =====================================================
    # 6. REVIEW SCORE
    # =====================================================

    reviews = product.get("reviews", 0)

    try:
        reviews = int(reviews)
    except (ValueError, TypeError):
        reviews = 0

    if reviews >= 5000:
        review_score = 5
    elif reviews >= 1000:
        review_score = 4
    elif reviews >= 500:
        review_score = 3
    elif reviews >= 100:
        review_score = 2
    elif reviews > 0:
        review_score = 1

    # =====================================================
    # TOTAL SCORE
    # =====================================================

    total_score = (
        category_score
        + budget_score
        + purpose_score
        + preference_score
        + rating_score
        + review_score
    )

    total_score = round(
        min(total_score, 100),
        2
    )

    # =====================================================
    # MATCH BREAKDOWN
    # =====================================================

    breakdown = {

        "category": {
            "score": category_score,
            "maximum": 25
        },

        "budget": {
            "score": budget_score,
            "maximum": 30
        },

        "purpose": {
            "score": purpose_score,
            "maximum": 20
        },

        "preferences": {
            "score": preference_score,
            "maximum": 15
        },

        "rating": {
            "score": round(rating_score, 2),
            "maximum": 5
        },

        "reviews": {
            "score": review_score,
            "maximum": 5
        }
    }

    return {
        "total_score": total_score,
        "breakdown": breakdown
    }


# =========================================================
# RECOMMEND PRODUCTS
# =========================================================

def recommend_products(products, requirements, limit=5):

    scored_products = []

    requested_category = requirements.get("category")

    # =====================================================
    # 1. FILTER BY CATEGORY AND STRICT REQUIREMENTS
    # =====================================================

    candidate_products = []

    for product in products:

        product_category = product.get("category", "")

        # Category filtering.

        if requested_category:

            if not category_matches(
                product_category,
                requested_category
            ):
                continue

        # Strict RAM and storage filtering.

        if not satisfies_strict_hardware_requirements(
            product,
            requirements
        ):
            continue

        candidate_products.append(product)

    # =====================================================
    # 2. CALCULATE SCORES
    # =====================================================

    for product in candidate_products:

        result = calculate_product_score(
            product,
            requirements
        )

        product_copy = product.copy()

        product_copy["match_score"] = result["total_score"]

        product_copy["match_breakdown"] = result["breakdown"]

        scored_products.append(product_copy)

    # =====================================================
    # 3. SORT
    # =====================================================

    scored_products.sort(
        key=lambda product: product.get("match_score", 0),
        reverse=True
    )

    # =====================================================
    # 4. RETURN TOP RESULTS
    # =====================================================

    return scored_products[:limit]
