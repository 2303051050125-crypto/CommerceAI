
import os
import json
import requests

from dotenv import load_dotenv

from services.product_service import load_products
from services.recommendation_service import recommend_products


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

MODEL = "openai/gpt-4o-mini"


# =========================================================
# GENERATE AI RESPONSE
# =========================================================

def generate_response(message, previous_context=None, previous_products=None):

    """
    Sends the user's message to OpenRouter.

    9A:
    Supports conversational shopping context.

    The AI identifies:
    - commerce intent
    - product category
    - budget
    - purpose
    - preferences

    Previous shopping requirements are preserved when
    the user sends a follow-up message.
    """

    # =====================================================
    # NORMALIZE PREVIOUS CONTEXT
    # =====================================================

    if not isinstance(previous_context, dict):
        previous_context = {}

    previous_category = previous_context.get("category")
    previous_budget = previous_context.get("budget")
    previous_purpose = previous_context.get("purpose")

    previous_preferences = previous_context.get(
        "preferences",
        []
    )

    if not isinstance(previous_preferences, list):
        previous_preferences = []

    # =====================================================
    # 9B: NORMALIZE PREVIOUS PRODUCTS
    # =====================================================

    if not isinstance(previous_products, list):
        previous_products = []

    previous_products = [
        product
        for product in previous_products
        if isinstance(product, dict)
    ]

    # =====================================================
    # 9C: PRODUCT REFERENCE HELPERS
    # =====================================================

    def product_name(product):
        return str(
            product.get("name")
            or product.get("product_name")
            or "Product"
        )

    def product_price(product):
        price = product.get("price")

        if price is None or price == "":
            return None

        try:
            return float(price)
        except (ValueError, TypeError):
            return None

    def find_referenced_products(user_message):
        text = str(user_message).lower()

        if not previous_products:
            return []

        # -------------------------------------------------
        # FIRST: Match explicitly mentioned product names
        # -------------------------------------------------

        name_matches = []

        for product in previous_products:

            name = product_name(product).strip().lower()

            if name and name != "product" and name in text:

                position = text.find(name)

                name_matches.append(
                    (position, product)
                )

        if name_matches:

            # Preserve the order in which products are
            # mentioned in the user's message.

            name_matches.sort(
                key=lambda item: item[0]
            )

            return [
                product
                for _, product in name_matches
            ]

        # -------------------------------------------------
        # SECOND: Match ordinal product references
        # -------------------------------------------------

        if (
            "first two" in text
            or "first 2" in text
            or "top two" in text
            or "top 2" in text
        ):
            return previous_products[:2]

        ordinal_map = {
            "first": 0,
            "1st": 0,
            "second": 1,
            "2nd": 1,
            "third": 2,
            "3rd": 2,
            "fourth": 3,
            "4th": 3,
            "fifth": 4,
            "5th": 4
        }

        for word, index in ordinal_map.items():

            if word in text and index < len(previous_products):
                return [previous_products[index]]

        return []
    # =====================================================
    # INITIALIZE PRODUCT REFERENCE VARIABLES
    # =====================================================

    lower_message = str(message).lower()

    reference_products = find_referenced_products(message)

    is_reference_query = bool(reference_products)

    is_battery_query = "battery" in lower_message

    is_comparison_query = any(
        phrase in lower_message
        for phrase in (
            "compare",
            "comparison",
            "difference between",
            "differences between",
            "versus",
            " vs "
        )
    )

    # =====================================================
    # CHECK API KEY
    # =====================================================

    if not OPENROUTER_API_KEY:
        return {
            "message": "❌ OpenRouter API key is missing.",
            "type": "error",
            "intent": "error",
            "category": None,
            "budget": None,
            "purpose": None,
            "preferences": [],
            "products": []
        }

    # =====================================================
    # HEADERS
    # =====================================================

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # =====================================================
    # AI SYSTEM PROMPT
    # =====================================================

    system_prompt = """
You are CommerceAI, an AI Personal Commerce Manager.

Your job is to understand natural-language shopping
requests and convert them into structured shopping
requirements that can be used by a product recommendation
engine.

The user may describe their requirements casually,
indirectly, or in multiple sentences.

You must identify:

1. intent
2. product category
3. budget
4. purpose
5. preferences


=========================================================
POSSIBLE INTENTS
=========================================================

- product_search
- product_comparison
- deal_search
- budget_analysis
- price_alert
- purchase_history
- general


=========================================================
OUTPUT FORMAT
=========================================================

Return ONLY valid JSON.

Use exactly this structure:

{
    "intent": "product_search",
    "category": "headphones",
    "budget": 35000,
    "purpose": "studying",
    "preferences": [
        "noise cancellation",
        "student"
    ],
    "response": "I found headphones suitable for studying within your budget."
}


=========================================================
1. NATURAL LANGUAGE UNDERSTANDING
=========================================================

Understand natural language.

The user does not have to explicitly say:

"category = headphones"

For example:

"I need something for listening to music while studying"

may indicate:

"category": "headphones"

when the context strongly suggests headphones.

Do not invent a category when there is not enough evidence.


=========================================================
2. BUDGET EXTRACTION
=========================================================

Understand different ways users express budgets.

Examples:

"under 40000"
"below ₹40,000"
"less than 40k"
"within 40k"
"I can spend up to 40,000"
"my budget is 40k"
"don't want to spend more than ₹35,000"

Convert these to a numeric value.

Examples:

"40k" -> 40000
"35k" -> 35000
"1 lakh" -> 100000
"1.5 lakh" -> 150000

budget must contain only a number.

If no new budget is provided, use the previous
conversation budget when one exists.

Otherwise:

"budget": null


=========================================================
3. PURPOSE EXTRACTION
=========================================================

Understand the reason the user wants the product.

Examples:

"for coding"
"for programming"
"for college"
"for studying"
"for gaming"
"for office work"
"for photography"
"for travelling"
"for music"

Normalize similar expressions.

Examples:

"coding" -> "programming"
"developer work" -> "programming"
"college studies" -> "studying"
"gaming" -> "gaming"

If the user does not provide a new purpose, preserve
the previous purpose when one exists.


=========================================================
4. PREFERENCE EXTRACTION
=========================================================

Extract specific features or preferences mentioned by
the user.

Examples:

"with noise cancellation"

-> ["noise cancellation"]

"good battery and lightweight"

-> ["good battery", "lightweight"]

"16GB RAM and 512GB SSD"

-> ["16GB RAM", "512GB SSD"]

"good camera"

-> ["good camera"]

Do NOT put the user's general purpose into preferences.

For example:

"laptop for gaming"

should produce:

"purpose": "gaming"

not:

"preferences": ["gaming"]


=========================================================
5. USER PROFILE / CONTEXT
=========================================================

The user may mention contextual information that affects
the shopping requirement.

For example:

"I'm a college student and need headphones for studying."

Extract:

"purpose": "studying"

and, when useful:

"preferences": ["student"]

Do not treat unrelated personal information as a
product requirement.


=========================================================
6. MULTIPLE REQUIREMENTS
=========================================================

The user may mention several requirements in one message.

Example:

"I'm a college student looking for a laptop for
programming and gaming. My budget is ₹70,000 and I want
at least 16GB RAM."

Return:

{
    "intent": "product_search",
    "category": "laptop",
    "budget": 70000,
    "purpose": "programming gaming",
    "preferences": [
        "student",
        "16GB RAM"
    ],
    "response": "I'll look for laptops under ₹70,000 suitable for programming and gaming."
}


=========================================================
7. DO NOT GUESS
=========================================================

Only extract information reasonably supported by the
user's message or previous shopping context.

If the user says:

"I need something good for college"

do not automatically assume:

"category": "laptop"

unless the surrounding context identifies the product.

Use null when information cannot be determined.


=========================================================
8. CATEGORY NORMALIZATION
=========================================================

Use simple category names that match the product database.

Examples:

"laptop computer" -> "laptop"
"notebook" -> "laptop"
"mobile" -> "smartphone"
"cell phone" -> "smartphone"
"headset" -> "headphones"

Use:

- laptop
- headphones
- smartphone
- tablet

when appropriate.


=========================================================
9. CONVERSATIONAL FOLLOW-UP
=========================================================

The user may send a follow-up message instead of repeating
their complete shopping requirements.

Previous requirements must be preserved.

For example:

Previous:

category = laptop
budget = 80000
purpose = programming
preferences = ["16GB RAM", "512GB SSD"]

User:

"Show me something with a better battery."

Preserve:

category = laptop
budget = 80000
purpose = programming
preferences = ["16GB RAM", "512GB SSD"]

and add:

"good battery"

to preferences.

Another example:

Previous:

category = laptop
budget = 80000
purpose = programming

User:

"What about gaming?"

Preserve:

category = laptop
budget = 80000

and change:

purpose = gaming

Another example:

Previous:

category = headphones
budget = 35000
purpose = studying
preferences = ["noise cancellation"]

User:

"Show me something lightweight."

Preserve:

category = headphones
budget = 35000
purpose = studying

and add:

"lightweight"

to preferences.


=========================================================
10. RESPONSE
=========================================================

The "response" field should be short and conversational.

Do not list all products.

Do not invent prices.

Do not invent product specifications.

The recommendation engine will handle product matching.


=========================================================
FINAL OUTPUT RULE
=========================================================

Return ONLY valid JSON.

Do not use Markdown.

Do not use ```json.

Do not add explanations before or after the JSON.
"""

    # =====================================================
    # 9A: ADD PREVIOUS SHOPPING CONTEXT
    # =====================================================

    context_prompt = f"""

=========================================================
PREVIOUS SHOPPING CONTEXT
=========================================================

The following context comes from earlier messages in the
same shopping conversation.

Previous category:
{previous_category}

Previous budget:
{previous_budget}

Previous purpose:
{previous_purpose}

Previous preferences:
{previous_preferences}

Previous recommended products:
{[product_name(product) for product in previous_products]}


=========================================================
9B / 9C PRODUCT REFERENCE RULES
=========================================================

Use the previous recommended products as the source of truth
for references such as "the first one", "the second one",
and "the first two".

Never invent product names, prices, or specifications.

If a requested specification is absent from the product data,
say that the available product data does not specify it.

For comparisons, use only fields present in the product data.


=========================================================
CONTEXT HANDLING RULES
=========================================================

Use the previous shopping context when the current message
is a follow-up.

Do not erase previous requirements just because the user
does not repeat them.

Only change a requirement when the user explicitly changes
it or provides a new requirement.

If the current message does not provide a new value for
category, preserve the previous category.

If the current message does not provide a new value for
budget, preserve the previous budget.

If the current message does not provide a new value for
purpose, preserve the previous purpose.

If the current message adds a new preference, preserve the
old preferences and add the new preference.

If the user explicitly removes a preference, remove that
preference.

If there is no previous context, extract requirements
normally from the current message.
"""

    system_prompt += context_prompt

    # =====================================================
    # SEND REQUEST TO OPENROUTER
    # =====================================================

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "temperature": 0.2
            },
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        # =================================================
        # EXTRACT AI RESPONSE
        # =================================================

        ai_text = (
            result["choices"][0]["message"]["content"]
        )

        # =================================================
        # CONVERT AI JSON TO PYTHON DICTIONARY
        # =================================================

        try:
            ai_data = json.loads(ai_text)

        except json.JSONDecodeError:

            print(
                "AI returned invalid JSON:",
                ai_text
            )

            return {
                "message": "⚠️ I received an invalid response from the AI service. Please try again.",
                "type": "error",
                "intent": "error",
                "category": previous_category,
                "budget": previous_budget,
                "purpose": previous_purpose,
                "preferences": previous_preferences,
                "products": []
            }

        # =================================================
        # EXTRACT STRUCTURED DATA
        # =================================================

        intent = ai_data.get("intent", "general")
        category = ai_data.get("category")
        budget = ai_data.get("budget")
        purpose = ai_data.get("purpose")

        preferences = ai_data.get(
            "preferences",
            []
        )

        # =================================================
        # 9A: MERGE WITH PREVIOUS CONTEXT
        # =================================================

        if category is None or str(category).strip() == "":
            category = previous_category

        if budget is None or budget == "":
            budget = previous_budget

        if purpose is None or str(purpose).strip() == "":
            purpose = previous_purpose

        if not isinstance(preferences, list):
            preferences = []

        merged_preferences = []

        for preference in previous_preferences:
            if preference not in merged_preferences:
                merged_preferences.append(preference)

        for preference in preferences:
            if preference not in merged_preferences:
                merged_preferences.append(preference)

        preferences = merged_preferences

        # =================================================
        # 3F: EXPLICIT REQUIREMENT MODIFICATION
        # =================================================

        change_text = str(message).lower().strip()

        # =================================================
        # 9C-4: CONTEXT-AWARE CORRECTIONS
        # =================================================

        correction_markers = (
            "actually",
            "sorry",
            "i meant",
            "i mean",
            "meant",
            "instead",
            "rather",
            "not ",
            "no,",
            "no "
        )

        correction_requested = any(
            marker in change_text
            for marker in correction_markers
        )

        category_aliases_9c4 = {
            "laptop": ["laptop", "laptops", "notebook", "notebooks", "laptop computer"],
            "headphones": ["headphones", "headphone", "headset", "headsets"],
            "smartphone": ["smartphone", "smartphones", "phone", "phones", "mobile", "mobiles", "cell phone", "cell phones"],
            "tablet": ["tablet", "tablets"]
        }

        def category_from_text_9c4(text):
            text = str(text).lower()

            for marker in (
                "i meant ",
                "i mean ",
                "meant ",
                "instead ",
                "rather "
            ):
                if marker in text:
                    tail = text.split(marker, 1)[1]

                    for canonical, aliases in category_aliases_9c4.items():
                        if any(alias in tail for alias in aliases):
                            return canonical

            for canonical, aliases in category_aliases_9c4.items():
                if any(alias in text for alias in aliases):
                    return canonical

            return None

        if correction_requested:

            corrected_category = category_from_text_9c4(change_text)

            if corrected_category:
                category = corrected_category

            budget_correction = None

            budget_patterns = (
                r"(?:i meant|i mean|meant|instead|budget is|make it)\s*(?:₹|rs\.?|inr\s*)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:k|thousand)?",
                r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:k|thousand)?"
            )

            import re

            for pattern in budget_patterns:
                match = re.search(pattern, change_text)

                if match:
                    raw_value = match.group(1).replace(",", "")

                    try:
                        value = float(raw_value)

                        if (
                            "k" in match.group(0).lower()
                            or "thousand" in match.group(0).lower()
                        ):
                            value *= 1000

                        budget_correction = (
                            int(value)
                            if value.is_integer()
                            else value
                        )

                        break

                    except ValueError:
                        pass

            if budget_correction is not None:
                budget = budget_correction

        # =================================================
        # 9C-3: EXPLICIT CONTEXT RESET / NEW SHOPPING TOPIC
        # =================================================

        reset_phrases = (
            "start over",
            "start again",
            "new search",
            "new shopping search",
            "new request",
            "forget everything",
            "forget my previous requirements",
            "forget previous requirements",
            "clear my requirements",
            "clear previous requirements",
            "reset my requirements",
            "reset the search",
            "start a new search",
            "let's start over",
            "lets start over"
        )

        reset_requested = any(
            phrase in change_text
            for phrase in reset_phrases
        )

        if reset_requested:

            previous_category = None
            previous_budget = None
            previous_purpose = None
            previous_preferences = []
            previous_products = []

            category = ai_data.get("category")
            budget = ai_data.get("budget")
            purpose = ai_data.get("purpose")
            preferences = ai_data.get("preferences", [])

            if not isinstance(preferences, list):
                preferences = []

            if not category:
                category = None

            if budget == "":
                budget = None

            if not purpose:
                purpose = None

        purpose_keywords = {
            "programming": [
                "programming", "coding", "developer",
                "development", "software development"
            ],
            "gaming": [
                "gaming", "gamer", "games"
            ],
            "studying": [
                "studying", "study", "college",
                "education", "learning"
            ],
            "office": [
                "office", "work", "business", "productivity"
            ],
            "photography": [
                "photography", "photograph", "photo"
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

        def purpose_from_text(text):
            for purpose_name, keywords in purpose_keywords.items():
                if any(keyword in text for keyword in keywords):
                    return purpose_name

            return None

        explicit_change = any(
            phrase in change_text
            for phrase in (
                "actually",
                "instead",
                "rather",
                "change my",
                "change the",
                "switch to",
                "make it",
                "i need it for",
                "i want it for"
            )
        )

        requested_purpose = purpose_from_text(change_text)

        if requested_purpose and (
            previous_purpose is None
            or requested_purpose != str(previous_purpose).lower().strip()
            or explicit_change
        ):
            purpose = requested_purpose

        removal_prefixes = (
            "forget ",
            "remove ",
            "drop ",
            "no longer need ",
            "don't need ",
            "do not need "
        )

        if previous_purpose:

            previous_purpose_text = str(
                previous_purpose
            ).lower().strip()

            purpose_removal = any(
                prefix + previous_purpose_text in change_text
                for prefix in removal_prefixes
            )

            if purpose_removal and not requested_purpose:
                purpose = None

        removal_requested = any(
            prefix in change_text
            for prefix in (
                "forget ",
                "remove ",
                "drop ",
                "no longer need ",
                "don't need ",
                "do not need "
            )
        )

        if removal_requested and (previous_preferences or preferences):

            preference_aliases = {
                "16gb ram": [
                    "16gb ram", "16 gb ram", "16gb",
                    "16 gb", "ram 16gb", "ram 16 gb"
                ],
                "512gb ssd": [
                    "512gb ssd", "512 gb ssd", "512gb",
                    "512 gb", "ssd 512gb", "ssd 512 gb"
                ],
                "noise cancellation": [
                    "noise cancellation",
                    "active noise cancellation",
                    "anc"
                ],
                "good battery": [
                    "good battery",
                    "long battery",
                    "long battery life",
                    "battery life"
                ],
                "lightweight": [
                    "lightweight",
                    "light weight",
                    "light",
                    "portable"
                ],
                "good camera": [
                    "good camera",
                    "high quality camera",
                    "camera"
                ]
            }

            def normalize_preference(value):
                text = str(value).lower().strip()
                text = text.replace("-", " ")
                text = " ".join(text.split())

                for canonical, aliases in preference_aliases.items():
                    if text == canonical or text in aliases:
                        return canonical

                return text

            removal_target_text = change_text

            for prefix in (
                "remove the ",
                "remove ",
                "forget the ",
                "forget ",
                "drop the ",
                "drop ",
                "no longer need the ",
                "no longer need ",
                "don't need the ",
                "don't need ",
                "do not need the ",
                "do not need "
            ):
                if prefix in removal_target_text:
                    removal_target_text = removal_target_text.split(
                        prefix, 1
                    )[1]
                    break

            for suffix in (
                " requirement",
                " requirements",
                " preference",
                " preferences",
                " anymore",
                " any more"
            ):
                if removal_target_text.endswith(suffix):
                    removal_target_text = removal_target_text[:-len(suffix)]

            removal_target_text = removal_target_text.strip(" .,!?:;")

            normalized_removal_target = normalize_preference(
                removal_target_text
            )

            kept_preferences = []

            for preference in preferences:

                normalized_preference = normalize_preference(
                    preference
                )

                remove_this = (
                    normalized_preference == normalized_removal_target
                    or normalized_removal_target in normalized_preference
                    or normalized_preference in normalized_removal_target
                )

                if not remove_this:
                    kept_preferences.append(preference)

            preferences = kept_preferences

        # =================================================
        # 9C-6: PERSISTENT BRAND PREFERENCE MEMORY
        # =================================================

        brand_preference_text = str(message).lower().strip()

        try:
            brand_catalog = load_products()
        except Exception:
            brand_catalog = []

        known_brands = []

        for catalog_product in brand_catalog:

            if not isinstance(catalog_product, dict):
                continue

            brand_value = catalog_product.get("brand")

            if brand_value:
                brand_value = str(brand_value).strip()

                if brand_value and brand_value.lower() not in [
                    item.lower() for item in known_brands
                ]:
                    known_brands.append(brand_value)

        preferred_brands = []
        excluded_brands = []

        explicit_brand_memory_update = False

        for brand in known_brands:

            brand_lower = brand.lower()

            preference_phrases = (
                f"prefer {brand_lower}",
                f"like {brand_lower}",
                f"want {brand_lower}",
                f"choose {brand_lower}",
                f"go with {brand_lower}",
                f"i'd prefer {brand_lower}",
                f"i would prefer {brand_lower}"
            )

            exclusion_phrases = (
                f"don't want {brand_lower}",
                f"do not want {brand_lower}",
                f"avoid {brand_lower}",
                f"exclude {brand_lower}",
                f"no {brand_lower}",
                f"not {brand_lower}"
            )

            if any(
                phrase in brand_preference_text
                for phrase in preference_phrases
            ):
                preferred_brands.append(brand)
                explicit_brand_memory_update = True

            if any(
                phrase in brand_preference_text
                for phrase in exclusion_phrases
            ):
                excluded_brands.append(brand)
                explicit_brand_memory_update = True

        for preference in previous_preferences:

            preference_text = str(preference).strip()
            lower_preference = preference_text.lower()

            if lower_preference.startswith("preferred brand:"):

                remembered_brand = preference_text.split(
                    ":", 1
                )[1].strip()

                if remembered_brand and remembered_brand.lower() not in [
                    item.lower() for item in preferred_brands
                ]:
                    preferred_brands.append(remembered_brand)

            elif lower_preference.startswith("excluded brand:"):

                remembered_brand = preference_text.split(
                    ":", 1
                )[1].strip()

                if remembered_brand and remembered_brand.lower() not in [
                    item.lower() for item in excluded_brands
                ]:
                    excluded_brands.append(remembered_brand)

        for brand in preferred_brands:

            memory_value = f"preferred brand: {brand}"

            if memory_value.lower() not in [
                str(item).lower() for item in preferences
            ]:
                preferences.append(memory_value)

        for brand in excluded_brands:

            memory_value = f"excluded brand: {brand}"

            if memory_value.lower() not in [
                str(item).lower() for item in preferences
            ]:
                preferences.append(memory_value)

        # =================================================
        # 9C-6: BRAND PREFERENCE / EXCLUSION HELPERS
        # =================================================

        def apply_brand_preferences_9c6(product_list):

            filtered_products = []

            for product in product_list:

                product_brand = str(
                    product.get("brand", "")
                ).strip()

                product_brand_lower = product_brand.lower()

                if excluded_brands and any(
                    product_brand_lower == str(brand).lower().strip()
                    for brand in excluded_brands
                ):
                    continue

                filtered_products.append(product)

            if preferred_brands:

                preferred_lower = [
                    str(brand).lower().strip()
                    for brand in preferred_brands
                ]

                preferred_products = [
                    product
                    for product in filtered_products
                    if str(product.get("brand", "")).lower().strip()
                    in preferred_lower
                ]

                if preferred_products:

                    other_products = [
                        product
                        for product in filtered_products
                        if product not in preferred_products
                    ]

                    return (
                        preferred_products + other_products
                    )[:5]

            return filtered_products[:5]

        # =================================================
        # 9C-7: PREFERENCE CORRECTION / CLEARING
        # =================================================

        preference_correction_text = str(message).lower().strip()

        clear_brand_memory = any(
            phrase in preference_correction_text
            for phrase in (
                "no longer care about the brand",
                "don't care about the brand",
                "do not care about the brand",
                "don't mind the brand",
                "do not mind the brand",
                "clear my brand preference",
                "clear brand preference",
                "forget my brand preference",
                "forget brand preference",
                "remove my brand preference",
                "remove brand preference"
            )
        )

        if clear_brand_memory:

            explicit_brand_memory_update = True
            preferred_brands = []
            excluded_brands = []

            preferences = [
                preference
                for preference in preferences
                if not str(preference).lower().startswith(
                    ("preferred brand:", "excluded brand:")
                )
            ]

        correction_signal = any(
            phrase in preference_correction_text
            for phrase in (
                "prefer ",
                "i'd prefer ",
                "i would prefer ",
                "rather have ",
                "rather choose ",
                "switch to ",
                "change my preference to ",
                "change the brand to ",
                "instead i want ",
                "instead, i want "
            )
        )

        correction_markers = (
            "actually",
            "instead",
            "rather",
            "changed my mind",
            "change my",
            "switch to",
            "now prefer"
        )

        is_preference_correction = (
            correction_signal
            and any(
                marker in preference_correction_text
                for marker in correction_markers
            )
        )

        if is_preference_correction and preferred_brands:

            latest_preferred = preferred_brands[-1]
            preferred_brands = [latest_preferred]

            excluded_brands = [
                brand
                for brand in excluded_brands
                if str(brand).lower().strip()
                != str(latest_preferred).lower().strip()
            ]

            preferences = [
                preference
                for preference in preferences
                if not str(preference).lower().startswith(
                    ("preferred brand:", "excluded brand:")
                )
            ]

        changed_mind_exclusion = any(
            phrase in preference_correction_text
            for phrase in (
                "i don't want ",
                "i do not want ",
                "i no longer want ",
                "i changed my mind about ",
                "avoid ",
                "exclude "
            )
        )

        if changed_mind_exclusion and excluded_brands:

            newly_excluded = excluded_brands[-1]

            preferred_brands = [
                brand
                for brand in preferred_brands
                if str(brand).lower().strip()
                != str(newly_excluded).lower().strip()
            ]

            preferences = [
                preference
                for preference in preferences
                if not (
                    str(preference).lower().startswith("preferred brand:")
                    and str(newly_excluded).lower().strip()
                    in str(preference).lower()
                )
            ]

        if preferred_brands or excluded_brands:

            preferences = [
                preference
                for preference in preferences
                if not str(preference).lower().startswith(
                    ("preferred brand:", "excluded brand:")
                )
            ]

            for brand in preferred_brands:
                preferences.append(f"preferred brand: {brand}")

            for brand in excluded_brands:
                preferences.append(f"excluded brand: {brand}")

        # =================================================
        # 9C-8: UNIFIED CONVERSATIONAL PREFERENCE STATE
        # =================================================

        unified_state_text = str(message).lower().strip()

        mentioned_brands_9c8 = []

        for brand in known_brands:

            brand_lower = str(brand).lower().strip()

            if brand_lower and brand_lower in unified_state_text:
                mentioned_brands_9c8.append(brand)

        clear_specific_brand = any(
            phrase in unified_state_text
            for phrase in (
                "forget ",
                "forget the ",
                "remove ",
                "clear ",
                "don't care about ",
                "do not care about ",
                "no longer care about "
            )
        ) and bool(mentioned_brands_9c8)

        if clear_specific_brand and not reset_requested:

            explicit_brand_memory_update = True

            clear_brands = {
                str(brand).lower().strip()
                for brand in mentioned_brands_9c8
            }

            preferred_brands = [
                brand
                for brand in preferred_brands
                if str(brand).lower().strip() not in clear_brands
            ]

            excluded_brands = [
                brand
                for brand in excluded_brands
                if str(brand).lower().strip() not in clear_brands
            ]

            preferences = [
                preference
                for preference in preferences
                if not any(
                    str(preference).lower().startswith(prefix)
                    and any(
                        brand_name in str(preference).lower()
                        for brand_name in clear_brands
                    )
                    for prefix in (
                        "preferred brand:",
                        "excluded brand:"
                    )
                )
            ]

        replacement_brand_signal = any(
            phrase in unified_state_text
            for phrase in (
                "make those ",
                "make it ",
                "switch to ",
                "change to ",
                "instead i want ",
                "instead, i want ",
                "actually, i want ",
                "actually i want ",
                "i want ",
                "i prefer ",
                "i'd prefer ",
                "i would prefer "
            )
        )

        if (
            replacement_brand_signal
            and mentioned_brands_9c8
            and not reset_requested
        ):

            explicit_brand_memory_update = True
            replacement_brand = mentioned_brands_9c8[-1]

            preferred_brands = [replacement_brand]

            excluded_brands = [
                brand
                for brand in excluded_brands
                if str(brand).lower().strip()
                != str(replacement_brand).lower().strip()
            ]

            preferences = [
                preference
                for preference in preferences
                if not str(preference).lower().startswith(
                    ("preferred brand:", "excluded brand:")
                )
            ]

        preferences = [
            preference
            for preference in preferences
            if not str(preference).lower().startswith(
                ("preferred brand:", "excluded brand:")
            )
        ]

        for brand in preferred_brands:
            preferences.append(f"preferred brand: {brand}")

        for brand in excluded_brands:
            preferences.append(f"excluded brand: {brand}")

        if reset_requested:
            previous_products = []

        # =================================================
        # END 9C-8
        # =================================================
        # =================================================
        # 9C-9: CONTEXT RECALL WITHOUT PRODUCT RECOMMENDATIONS
        # =================================================

        context_recall_phrases = (
            "what is my current",
            "what are my current",
            "what was my",
            "remind me of my",
            "tell me my current",
            "what's my current",
            "what is my category",
            "what is my budget",
            "what is my purpose",
            "what are my requirements"
        )

        is_context_recall = any(
            phrase in lower_message
            for phrase in context_recall_phrases
        )

        if is_context_recall:

            return {
                "message": (
                    f"Your current category is {category or 'not specified'}, "
                    f"your budget is "
                    f"{'₹' + format(float(budget), ',.0f') if budget is not None else 'not specified'}, "
                    f"and your purpose is {purpose or 'not specified'}."
                ),
                "type": "general",
                "intent": "general",
                "category": category,
                "budget": budget,
                "purpose": purpose,
                "preferences": preferences,
                "products": []
            }
        # =================================================
        # 9C-2: SMART CLARIFICATION
        # =================================================

        has_previous_shopping_context = any([
            previous_category,
            previous_budget,
            previous_purpose,
            previous_preferences,
            previous_products
        ])

        if not has_previous_shopping_context:

            shopping_intents = (
                "product_search",
                "deal_search",
                "general"
            )

            shopping_language_present = any(
                word in lower_message
                for word in (
                    "need",
                    "want",
                    "looking for",
                    "find me",
                    "show me",
                    "buy",
                    "shopping",
                    "recommend",
                    "recommendation"
                )
            )

            if (
                category is None
                and intent in shopping_intents
                and shopping_language_present
            ):
                return {
                    "message": (
                        "Sure — what type of product are you looking for? "
                        "For example, a laptop, headphones, smartphone, or tablet."
                    ),
                    "type": "general",
                    "intent": "general",
                    "category": None,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences,
                    "products": []
                }

            if (
                category
                and budget is None
                and intent in (
                    "product_search",
                    "deal_search"
                )
            ):
                return {
                    "message": (
                        f"Great — I'll help you find a {category}. "
                        "What's your budget?"
                    ),
                    "type": "general",
                    "intent": "general",
                    "category": category,
                    "budget": None,
                    "purpose": purpose,
                    "preferences": preferences,
                    "products": []
                }

            if (
                category
                and budget is not None
                and purpose is None
                and intent in (
                    "product_search",
                    "deal_search"
                )
            ):
                return {
                    "message": (
                        "What will you mainly use it for — coding, gaming, "
                        "studying, office work, photography, or something else?"
                    ),
                    "type": "general",
                    "intent": "general",
                    "category": category,
                    "budget": budget,
                    "purpose": None,
                    "preferences": preferences,
                    "products": []
                }

        # =================================================
        # 9C-5: CONSTRAINT CONFLICT / NO-RESULT RECOVERY
        # =================================================

        def category_matches_9c5(product_category, requested_category):

            if not product_category or not requested_category:
                return False

            product_value = str(product_category).lower().strip()
            requested_value = str(requested_category).lower().strip()

            aliases = {
                "headphones": {
                    "headphones", "headphone", "headset", "headsets"
                },
                "laptop": {
                    "laptop", "laptops", "notebook", "notebooks"
                },
                "smartphone": {
                    "smartphone", "smartphones", "phone", "phones",
                    "mobile", "mobiles", "cell phone", "cell phones"
                },
                "tablet": {
                    "tablet", "tablets"
                }
            }

            requested_aliases = aliases.get(
                requested_value,
                {requested_value}
            )

            return (
                product_value in requested_aliases
                or requested_value == product_value
            )

        if (
            category is not None
            and intent in ("product_search", "deal_search")
            and not reference_products
        ):

            try:

                catalog_for_conflict = load_products()

                category_products = [
                    product
                    for product in catalog_for_conflict
                    if isinstance(product, dict)
                    and category_matches_9c5(
                        product.get("category"),
                        category
                    )
                ]

                if not category_products:

                    return {
                        "message": (
                            f"I couldn't find any {category} products in the "
                            "current product catalog. You can try another "
                            "product category."
                        ),
                        "type": "general",
                        "intent": "general",
                        "category": category,
                        "budget": budget,
                        "purpose": purpose,
                        "preferences": preferences,
                        "products": []
                    }

                numeric_budget = None

                try:
                    if budget is not None and budget != "":
                        numeric_budget = float(budget)
                except (ValueError, TypeError):
                    numeric_budget = None

                if numeric_budget is not None:

                    priced_category_products = [
                        product
                        for product in category_products
                        if product_price(product) is not None
                    ]

                    if priced_category_products:

                        cheapest_product = min(
                            priced_category_products,
                            key=lambda product: product_price(product)
                        )

                        cheapest_price = product_price(cheapest_product)

                        if cheapest_price > numeric_budget:

                            return {
                                "message": (
                                    f"I couldn't find a {category} within "
                                    f"₹{numeric_budget:,.0f}. The lowest-priced "
                                    f"{category} in the current catalog is "
                                    f"{product_name(cheapest_product)} at "
                                    f"₹{cheapest_price:,.0f}. Would you like "
                                    "to increase your budget?"
                                ),
                                "type": "general",
                                "intent": "general",
                                "category": category,
                                "budget": budget,
                                "purpose": purpose,
                                "preferences": preferences,
                                "products": []
                            }

            except Exception as error:

                print(
                    "9C-5 Constraint Check Error:",
                    error
                )

        # =================================================
        # DETERMINE PRODUCT SEARCH
        # =================================================

        has_product_context = (
            category is not None
            or budget is not None
            or purpose is not None
            or len(preferences) > 0
        )

        if (
            has_product_context
            and intent == "general"
        ):
            intent = "product_search"

        # =================================================
        # 9C: BUILD A STABLE PREVIOUS PRODUCT LIST
        # =================================================

        if len(previous_products) < 2 and category is not None:

            try:

                all_products_for_context = load_products()

                context_requirements = {
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences
                }

                rebuilt_products = recommend_products(
                    all_products_for_context,
                    context_requirements,
                    limit=5
                )

                if len(rebuilt_products) >= len(previous_products):
                    previous_products = rebuilt_products

            except Exception as error:

                print(
                    "Previous Product Context Error:",
                    error
                )

        # -------------------------------------------------
        # Prevent stale product references after a category
        # reset/correction.
        # -------------------------------------------------

        if category and previous_products:

            requested_category_text = str(
                category
            ).lower().strip()

            category_aliases_for_context = {
                "laptop": {
                    "laptop",
                    "laptops",
                    "notebook",
                    "notebooks"
                },
                "headphones": {
                    "headphone",
                    "headphones",
                    "headset",
                    "headsets"
                },
                "smartphone": {
                    "phone",
                    "phones",
                    "smartphone",
                    "smartphones",
                    "mobile",
                    "mobiles"
                },
                "tablet": {
                    "tablet",
                    "tablets"
                }
            }

            requested_category_aliases = (
                category_aliases_for_context.get(
                    requested_category_text,
                    {requested_category_text}
                )
            )

            category_compatible_products = []

            for product in previous_products:

                product_category_text = str(
                    product.get("category", "")
                ).lower().strip()

                if product_category_text in requested_category_aliases:
                    category_compatible_products.append(product)

            if not category_compatible_products:
                previous_products = []

        reference_products = find_referenced_products(message)

        if is_battery_query and previous_products:
            reference_products = previous_products

        is_reference_query = bool(reference_products)

        # =================================================
        # 3D: SMART FOLLOW-UP PRODUCT ACTIONS
        # =================================================

        def product_text(product):

            values = [
                product.get("name", ""),
                product.get("brand", ""),
                product.get("category", ""),
                product.get("description", ""),
                product.get("processor", ""),
                product.get("ram", ""),
                product.get("storage", ""),
                product.get("display", ""),
                product.get("battery", "")
            ]

            features = product.get("features", [])

            if isinstance(features, list):
                values.extend(features)
            elif features:
                values.append(features)

            tags = product.get("tags", [])

            if isinstance(tags, list):
                values.extend(tags)
            elif tags:
                values.append(tags)

            return " ".join(
                str(value).lower()
                for value in values
                if value is not None and str(value).strip()
            )

        def product_rating(product):
            try:
                return float(product.get("rating", 0) or 0)
            except (ValueError, TypeError):
                return 0.0

        def product_reviews(product):
            try:
                return int(product.get("reviews", 0) or 0)
            except (ValueError, TypeError):
                return 0

        def product_match_score(product):
            try:
                return float(product.get("match_score", 0) or 0)
            except (ValueError, TypeError):
                return 0.0

        def money_text(product):

            price = product_price(product)

            if price is None:
                return "price not specified"

            return f"₹{price:,.0f}"

        def return_selected_product(product, message_text):

            return {
                "message": message_text,
                "type": "product_search",
                "intent": "product_search",
                "category": category,
                "budget": budget,
                "purpose": purpose,
                "preferences": preferences,
                "products": [product],
                "selected_product": product
            }

        def return_selected_products(selected_products, message_text):

            return {
                "message": message_text,
                "type": "product_search",
                "intent": "product_search",
                "category": category,
                "budget": budget,
                "purpose": purpose,
                "preferences": preferences,
                "products": selected_products,
                "selected_product": (
                    selected_products[0]
                    if len(selected_products) == 1
                    else None
                )
            }

        if previous_products:

            # =================================================
            # 3G: MULTI-TURN RECOMMENDATION REFINEMENT
            # =================================================

            def product_identity(product):

                return (
                    str(
                        product.get("id")
                        or product.get("product_id")
                        or product_name(product)
                    ).strip().lower()
                )

            def current_requirement_set():

                return {
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences
                }

            def regenerate_products(exclude_products=None, limit=5):

                exclude_products = exclude_products or []

                excluded_ids = {
                    product_identity(product)
                    for product in exclude_products
                }

                try:

                    all_products = load_products()

                    candidates = [
                        product
                        for product in all_products
                        if product_identity(product) not in excluded_ids
                    ]

                    return recommend_products(
                        candidates,
                        current_requirement_set(),
                        limit=limit
                    )

                except Exception as error:

                    print(
                        "3G Alternative Recommendation Error:",
                        error
                    )

                    return []

            # -------------------------------------------------
            # Show top N / first N products
            # -------------------------------------------------

            import re

            top_match = re.search(
                r"\b(?:top|first)\s*(\d+)\b",
                lower_message
            )

            if top_match and any(
                phrase in lower_message
                for phrase in (
                    "show",
                    "give me",
                    "display",
                    "only",
                    "recommend"
                )
            ):

                requested_count = max(
                    1,
                    min(
                        int(top_match.group(1)),
                        len(previous_products)
                    )
                )

                selected = previous_products[:requested_count]

                return return_selected_products(
                    selected,
                    f"I'm showing the top {requested_count} recommended products."
                )

            # -------------------------------------------------
            # Find alternatives / different products
            # -------------------------------------------------

            wants_alternatives = any(
                phrase in lower_message
                for phrase in (
                    "show alternatives",
                    "give me alternatives",
                    "find alternatives",
                    "different ones",
                    "something different",
                    "other options",
                    "other products",
                    "new options",
                    "new products",
                    "i don't like any of these",
                    "i dont like any of these",
                    "i don't like these",
                    "i dont like these"
                )
            )

            if wants_alternatives:

                alternatives = regenerate_products(
                    exclude_products=previous_products,
                    limit=5
                )

                if alternatives:

                    return return_selected_products(
                        alternatives,
                        "I found alternative products using your current requirements."
                    )

                return return_selected_products(
                    [],
                    "I couldn't find different products matching your current requirements."
                )

            # -------------------------------------------------
            # Cheaper alternatives with the same requirements
            # -------------------------------------------------

            wants_cheaper_alternatives = (
                any(
                    phrase in lower_message
                    for phrase in (
                        "cheaper alternatives",
                        "cheaper options",
                        "cheaper products",
                        "something cheaper",
                        "give me cheaper",
                        "show me cheaper"
                    )
                )
                and not any(
                    phrase in lower_message
                    for phrase in (
                        "cheaper one",
                        "cheaper dell",
                        "cheaper acer",
                        "cheaper hp",
                        "cheaper lenovo",
                        "cheaper asus"
                    )
                )
            )

            if wants_cheaper_alternatives:

                alternatives = regenerate_products(
                    exclude_products=previous_products,
                    limit=10
                )

                priced_alternatives = [
                    product
                    for product in alternatives
                    if product_price(product) is not None
                ]

                if priced_alternatives:

                    current_prices = [
                        product_price(product)
                        for product in previous_products
                        if product_price(product) is not None
                    ]

                    if current_prices:

                        reference_price = min(current_prices)

                        priced_alternatives = [
                            product
                            for product in priced_alternatives
                            if product_price(product) < reference_price
                        ]

                    priced_alternatives.sort(
                        key=product_price
                    )

                    selected = priced_alternatives[:5]

                    if selected:

                        return return_selected_products(
                            selected,
                            "I found cheaper alternatives while keeping your current requirements."
                        )

                return return_selected_products(
                    [],
                    "I couldn't find cheaper alternatives matching your current requirements."
                )

            # -------------------------------------------------
            # Similar product
            # -------------------------------------------------

            wants_similar = any(
                phrase in lower_message
                for phrase in (
                    "similar to",
                    "similar product",
                    "something similar",
                    "like this one",
                    "like that one"
                )
            )

            if wants_similar:

                target = None

                for product in previous_products:

                    name = product_name(product).lower()

                    if name != "product" and name in lower_message:
                        target = product
                        break

                if target is None and reference_products:
                    target = reference_products[0]

                if target is not None:

                    target_text = product_text(target)

                    target_tokens = {
                        token
                        for token in target_text.split()
                        if len(token) >= 4
                    }

                    candidates = []

                    try:

                        all_products = load_products()

                        for product in all_products:

                            if product_identity(product) == product_identity(target):
                                continue

                            if (
                                category
                                and str(product.get("category", "")).lower()
                                != str(category).lower()
                            ):
                                continue

                            candidate_tokens = {
                                token
                                for token in product_text(product).split()
                                if len(token) >= 4
                            }

                            overlap = len(
                                target_tokens & candidate_tokens
                            )

                            if overlap > 0:
                                candidates.append((overlap, product))

                        candidates.sort(
                            key=lambda item: (
                                item[0],
                                product_match_score(item[1]),
                                product_rating(item[1])
                            ),
                            reverse=True
                        )

                        similar_products = [
                            product
                            for _, product in candidates[:5]
                        ]

                        if similar_products:

                            return return_selected_products(
                                similar_products,
                                f"I found products similar to {product_name(target)} using the available product data."
                            )

                    except Exception as error:

                        print(
                            "3G Similar Product Error:",
                            error
                        )

            # -------------------------------------------------
            # Keep the same requirements, but refresh the list
            # -------------------------------------------------

            wants_refresh = any(
                phrase in lower_message
                for phrase in (
                    "refresh the recommendations",
                    "refresh recommendations",
                    "find more",
                    "show more options",
                    "more options",
                    "more recommendations"
                )
            )

            if wants_refresh:

                refreshed = regenerate_products(
                    exclude_products=previous_products,
                    limit=5
                )

                if refreshed:

                    return return_selected_products(
                        refreshed,
                        "Here are more options using your current requirements."
                    )

            # =================================================
            # 3E: NATURAL PRODUCT SELECTION / FILTERING
            # =================================================

            def matching_brand_products():

                matches = []

                for product in previous_products:

                    brand = str(
                        product.get("brand", "")
                    ).strip()

                    if brand and brand.lower() in lower_message:
                        matches.append(product)

                return matches

            def matching_name_products():

                matches = []

                for product in previous_products:

                    name = product_name(product).strip().lower()

                    if name and name != "product" and name in lower_message:
                        matches.append(product)

                return matches

            brand_matches = matching_brand_products()
            name_matches = matching_name_products()

            if any(
                phrase in lower_message
                for phrase in (
                    "show only the first two",
                    "show the first two",
                    "show only first two",
                    "give me the first two",
                    "only the first two"
                )
            ):

                selected = previous_products[:2]

                return return_selected_products(
                    selected,
                    "I'm showing the first two recommended products."
                )

            wants_remove = any(
                phrase in lower_message
                for phrase in (
                    "remove ",
                    "exclude ",
                    "don't show ",
                    "do not show ",
                    "hide "
                )
            )

            if wants_remove:

                removal_terms = []

                for product in previous_products:

                    brand = str(
                        product.get("brand", "")
                    ).strip().lower()

                    name = product_name(product).strip().lower()

                    if brand and brand in lower_message:
                        removal_terms.append(("brand", brand))

                    if name and name != "product" and name in lower_message:
                        removal_terms.append(("name", name))

                if removal_terms:

                    remaining = []

                    for product in previous_products:

                        brand = str(
                            product.get("brand", "")
                        ).strip().lower()

                        name = product_name(product).strip().lower()

                        should_remove = any(
                            (kind == "brand" and brand == value)
                            or
                            (kind == "name" and name == value)
                            for kind, value in removal_terms
                        )

                        if not should_remove:
                            remaining.append(product)

                    if remaining:

                        removed_names = [
                            product_name(product)
                            for product in previous_products
                            if product not in remaining
                        ]

                        return return_selected_products(
                            remaining,
                            "Removed " + ", ".join(removed_names) + "."
                        )

            explicit_matches = name_matches or brand_matches

            if explicit_matches:

                wants_show = any(
                    phrase in lower_message
                    for phrase in (
                        "show",
                        "give me",
                        "i want",
                        "i'll take",
                        "take",
                        "choose",
                        "select",
                        "prefer",
                        "like"
                    )
                )

                if wants_show:

                    if len(explicit_matches) == 1:

                        selected = explicit_matches[0]

                        return return_selected_product(
                            selected,
                            f"I'm showing {product_name(selected)} at {money_text(selected)}."
                        )

                    return return_selected_products(
                        explicit_matches,
                        "I'm showing the matching products from the previous recommendations."
                    )

            wants_cheaper_brand = (
                brand_matches
                and any(
                    phrase in lower_message
                    for phrase in (
                        "cheaper",
                        "lowest price",
                        "cheapest",
                        "less expensive"
                    )
                )
            )

            if wants_cheaper_brand:

                priced = [
                    product
                    for product in brand_matches
                    if product_price(product) is not None
                ]

                if priced:

                    selected = min(
                        priced,
                        key=product_price
                    )

                    return return_selected_product(
                        selected,
                        f"The cheaper {selected.get('brand')} option is {product_name(selected)} at {money_text(selected)}."
                    )

            wants_cheaper = any(
                phrase in lower_message
                for phrase in (
                    "cheaper one",
                    "cheaper",
                    "less expensive",
                    "lower price",
                    "lowest price",
                    "cheapest"
                )
            )

            wants_more_expensive = any(
                phrase in lower_message
                for phrase in (
                    "more expensive",
                    "higher price",
                    "most expensive",
                    "costlier"
                )
            )

            if wants_cheaper:

                priced = [
                    product
                    for product in previous_products
                    if product_price(product) is not None
                ]

                if priced:

                    selected = min(
                        priced,
                        key=product_price
                    )

                    return return_selected_product(
                        selected,
                        f"The cheaper option is {product_name(selected)} at {money_text(selected)}."
                    )

            if wants_more_expensive:

                priced = [
                    product
                    for product in previous_products
                    if product_price(product) is not None
                ]

                if priced:

                    selected = max(
                        priced,
                        key=product_price
                    )

                    return return_selected_product(
                        selected,
                        f"The more expensive option is {product_name(selected)} at {money_text(selected)}."
                    )

            if any(
                phrase in lower_message
                for phrase in (
                    "best rated",
                    "highest rated",
                    "highest rating",
                    "better rated",
                    "best rating"
                )
            ):

                selected = max(
                    previous_products,
                    key=product_rating
                )

                return return_selected_product(
                    selected,
                    f"{product_name(selected)} has the highest rating among the referenced products at {product_rating(selected):g}/5."
                )

            if any(
                phrase in lower_message
                for phrase in (
                    "most reviews",
                    "most popular",
                    "highest reviews"
                )
            ):

                selected = max(
                    previous_products,
                    key=product_reviews
                )

                return return_selected_product(
                    selected,
                    f"{product_name(selected)} has the most reviews among the referenced products with {product_reviews(selected):,} reviews."
                )

            if any(
                phrase in lower_message
                for phrase in (
                    "better for gaming",
                    "best for gaming",
                    "better for coding",
                    "best for coding",
                    "better for programming",
                    "best for programming",
                    "better for studying",
                    "best for studying",
                    "better for office",
                    "best for office",
                    "which is better",
                    "which one is better",
                    "which should i buy",
                    "which one should i buy"
                )
            ):

                selected = max(
                    previous_products,
                    key=product_match_score
                )

                score = product_match_score(selected)

                if score > 0:

                    score_details = []

                    for product in previous_products:

                        product_score = product_match_score(product)

                        if product_score > 0:

                            score_details.append(
                                f"{product_name(product)}: {product_score:g}% match"
                            )

                    comparison_text = "; ".join(score_details)

                    return return_selected_product(
                        selected,
                        f"For this request, {product_name(selected)} has the highest recommendation match at {score:g}%. "
                        f"Among the referenced products: {comparison_text}."
                    )

            preference_match = None

            brand_words = lower_message.replace(".", " ").split()

            for product in previous_products:

                brand = str(
                    product.get("brand", "")
                ).strip()

                if not brand:
                    continue

                brand_lower = brand.lower()

                if (
                    ("prefer" in lower_message or "like" in lower_message)
                    and brand_lower in brand_words
                ):
                    preference_match = product
                    break

            if preference_match is not None:

                return return_selected_product(
                    preference_match,
                    f"You prefer {preference_match.get('brand')}, so I'm showing {product_name(preference_match)} at {money_text(preference_match)}."
                )

        # =================================================
        # 9C: DETERMINISTIC PRODUCT REFERENCE HANDLING
        # =================================================

        if is_reference_query and previous_products:

            products = reference_products

            if is_battery_query:

                battery_values = []

                for product in reference_products:

                    battery = product.get("battery")

                    if battery is None or battery == "":

                        features = product.get("features", [])

                        if isinstance(features, list):

                            matches = [
                                str(feature)
                                for feature in features
                                if "battery" in str(feature).lower()
                            ]

                            if matches:
                                battery = " | ".join(matches)

                    if battery is not None and battery != "":

                        battery_values.append(
                            f"{product_name(product)}: {battery}"
                        )

                if battery_values:

                    response_message = (
                        "Battery information available for the referenced "
                        "products: " + "; ".join(battery_values)
                    )

                else:

                    response_message = (
                        "The available product data does not specify "
                        "battery information."
                    )

                return {
                    "message": response_message,
                    "type": "product_comparison",
                    "intent": "product_comparison",
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences,
                    "products": products
                }

            if is_comparison_query and len(reference_products) >= 2:

                first = reference_products[0]
                second = reference_products[1]

                comparison_lines = [
                    f"Comparison: {product_name(first)} vs "
                    f"{product_name(second)}."
                ]

                def get_comparison_value(product, key):

                    # 1. Check direct product fields
                    value = product.get(key)

                    if value is not None and value != "":
                        return str(value)

                    # 2. Check specifications dictionary
                    specifications = product.get(
                        "specifications",
                        {}
                    )

                    if isinstance(specifications, dict):

                        value = specifications.get(key)

                        if value is not None and value != "":
                            return str(value)

                    # 3. Check features list
                    features = product.get("features", [])

                    if not isinstance(features, list):
                        return None

                    aliases = {
                        "ram": ("ram",),
                        "storage": ("ssd", "storage", "hdd"),
                        "processor": (
                            "processor",
                            "intel core",
                            "amd ryzen",
                            "snapdragon",
                            "apple m"
                        ),
                        "display": (
                            "display",
                            "full hd",
                            "amoled",
                            "oled",
                            "ips"
                        ),
                        "battery": ("battery",)
                    }

                    keywords = aliases.get(key, ())

                    for feature in features:

                        feature_text = str(feature).strip()

                        if any(
                            keyword in feature_text.lower()
                            for keyword in keywords
                        ):
                            return feature_text

                    return None

                for label, key in (
                    ("Price", "price"),
                    ("Brand", "brand"),
                    ("Category", "category"),
                    ("Rating", "rating"),
                    ("Reviews", "reviews"),
                    ("Processor", "processor"),
                    ("RAM", "ram"),
                    ("Storage", "storage"),
                    ("Display", "display"),
                    ("Battery", "battery")
                ):

                    left = get_comparison_value(first, key)
                    right = get_comparison_value(second, key)

                    if (
                        (left is not None and left != "")
                        or
                        (right is not None and right != "")
                    ):

                        left_text = (
                            str(left)
                            if left is not None
                            else "Not specified"
                        )

                        right_text = (
                            str(right)
                            if right is not None
                            else "Not specified"
                        )

                        comparison_lines.append(
                            f"{label}: {left_text} vs {right_text}"
                        )

                comparison_lines.append(
                    "Only specifications present in the product data are shown."
                )

                return {
                    "message": "\n".join(comparison_lines),
                    "type": "product_comparison",
                    "intent": "product_comparison",
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences,
                    "products": products
                }
        # =================================================
        # 10B-6: RECOMMENDATION FAILURE TRACKING
        # =================================================

        recommendation_failed = False

        # =================================================
        # PRODUCT RECOMMENDATION
        # =================================================

        products = []

        if intent == "product_search":

            try:

                all_products = load_products()

                requirements = {
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences
                }

                products = recommend_products(
                    all_products,
                    requirements,
                    limit=5
                )

                products = apply_brand_preferences_9c6(products)

                print("\n========================================")
                print("AI PRODUCT RECOMMENDATIONS")
                print("========================================")

                print("Category:", category)
                print("Budget:", budget)
                print("Purpose:", purpose)
                print("Preferences:", preferences)

                print("\nRanked Products:")

                for product in products:

                    print(
                        product.get("name", "Unknown"),
                        "->",
                        product.get("match_score", 0),
                        "% Match"
                    )

                print("========================================\n")

            except Exception as error:

                print(
                    "Recommendation Engine Error:",
                    error
                )

                products = []
                recommendation_failed = True

        # =================================================
        # DEAL SEARCH
        # =================================================

        elif intent == "deal_search":

            try:

                all_products = load_products()

                requirements = {
                    "category": category,
                    "budget": budget,
                    "purpose": purpose,
                    "preferences": preferences
                }

                products = recommend_products(
                    all_products,
                    requirements,
                    limit=5
                )

                products = apply_brand_preferences_9c6(products)

            except Exception as error:

                print(
                    "Deal Search Error:",
                    error
                )

                products = []
                recommendation_failed = True

        # =================================================
        # 10B-6: RETURN SAFE ERROR IF RECOMMENDATION FAILS
        # =================================================

        if recommendation_failed:

            return {
                "message": (
                    "⚠️ I'm having trouble generating product "
                    "recommendations right now. Please try again "
                    "in a moment."
                ),
                "type": "error",
                "intent": "error",
                "category": category,
                "budget": budget,
                "purpose": purpose,
                "preferences": preferences,
                "products": []
            }

        # =================================================
        # RETURN COMPLETE RESPONSE
        # =================================================

        response_message = ai_data.get(
            "response",
            "I understand your request."
        )

        if explicit_brand_memory_update and preferred_brands:

            response_message = (
                f"I'll remember that you prefer "
                f"{preferred_brands[0]} and prioritize it in your "
                "future recommendations."
            )

        elif explicit_brand_memory_update and excluded_brands:

            response_message = (
                f"I'll remember that you don't want "
                f"{excluded_brands[0]} and exclude it from future "
                "recommendations when possible."
            )

        return {
            "message": response_message,
            "type": intent,
            "intent": intent,
            "category": category,
            "budget": budget,
            "purpose": purpose,
            "preferences": preferences,
            "products": products
        }

    # =====================================================
    # OPENROUTER REQUEST ERROR
    # =====================================================

    except requests.exceptions.RequestException as error:

        print(
            "OpenRouter API Error:",
            error
        )

        return {
            "message": "⚠️ I couldn't connect to the AI service.",
            "type": "error",
            "intent": "error",
            "category": None,
            "budget": None,
            "purpose": None,
            "preferences": [],
            "products": []
        }

    # =====================================================
    # GENERAL ERROR
    # =====================================================

    except Exception as error:

        print(
            "AI Service Error:",
            error
        )

        return {
            "message": "⚠️ Something went wrong while processing your request.",
            "type": "error",
            "intent": "error",
            "category": None,
            "budget": None,
            "purpose": None,
            "preferences": [],
            "products": []
        }
