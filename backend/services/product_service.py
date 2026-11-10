
import json
import os
import re
from copy import deepcopy


# =========================================================
# PRODUCT DATABASE
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PRODUCT_FILE = os.path.join(
    BASE_DIR,
    "database",
    "products.json"
)


# =========================================================
# CATEGORY ALIASES
# =========================================================

CATEGORY_ALIASES = {

    "laptop": [
        "laptop",
        "laptops",
        "notebook",
        "notebooks"
    ],

    "headphones": [
        "headphone",
        "headphones",
        "headset",
        "headsets"
    ],

    "smartphone": [
        "smartphone",
        "smartphones",
        "phone",
        "phones",
        "mobile",
        "mobiles",
        "cell phone",
        "cell phones"
    ],

    "tablet": [
        "tablet",
        "tablets"
    ],

    "smartwatch": [
        "smartwatch",
        "smartwatches",
        "smart watch",
        "smart watches"
    ],

    "monitor": [
        "monitor",
        "monitors",
        "display",
        "displays"
    ],

    "keyboard": [
        "keyboard",
        "keyboards"
    ],

    "mouse": [
        "mouse",
        "mice"
    ]
}


# =========================================================
# CATEGORY NORMALIZATION
# =========================================================

def normalize_category(category):
    """
    Converts category aliases into a consistent category name.
    """

    if not isinstance(category, str):
        return None

    category = category.lower().strip()

    for canonical, aliases in CATEGORY_ALIASES.items():

        if category in aliases:
            return canonical

    return category


# =========================================================
# CATEGORY MATCHING
# =========================================================

def category_matches(product_category, requested_category):
    """
    Checks whether two categories represent the same product type.
    """

    if not requested_category:
        return True

    normalized_product = normalize_category(
        product_category
    )

    normalized_requested = normalize_category(
        requested_category
    )

    if not normalized_product or not normalized_requested:
        return False

    return normalized_product == normalized_requested


# =========================================================
# PRODUCT RECORD VALIDATION
# =========================================================

def validate_product(product):
    """
    Validates an individual product record.

    Invalid records are rejected.
    Existing product fields are preserved.

    Supports both old and new product structures.
    """

    if not isinstance(product, dict):
        return False

    # -----------------------------------------------------
    # REQUIRED FIELDS
    # -----------------------------------------------------

    required_fields = [
        "id",
        "name",
        "category",
        "price"
    ]

    for field in required_fields:

        if field not in product:
            return False

        if product[field] is None:
            return False

    # -----------------------------------------------------
    # NAME VALIDATION
    # -----------------------------------------------------

    if not isinstance(product.get("name"), str):
        return False

    if not product["name"].strip():
        return False

    # -----------------------------------------------------
    # CATEGORY VALIDATION
    # -----------------------------------------------------

    if not isinstance(product.get("category"), str):
        return False

    if not product["category"].strip():
        return False

    # -----------------------------------------------------
    # PRICE VALIDATION
    # -----------------------------------------------------

    try:

        price = float(product["price"])

        if price < 0:
            return False

    except (ValueError, TypeError):
        return False

    # -----------------------------------------------------
    # OPTIONAL FIELD VALIDATION
    # -----------------------------------------------------

    if "features" in product:

        if not isinstance(product["features"], (list, str)):
            return False

    if "tags" in product:

        if not isinstance(product["tags"], (list, str)):
            return False

    if "specifications" in product:

        if not isinstance(product["specifications"], dict):
            return False

    return True


# =========================================================
# NORMALIZE PRODUCT SPECIFICATIONS
# =========================================================

def normalize_product_specifications(product):
    """
    Supports structured specifications while preserving
    compatibility with existing top-level product fields.

    Does not invent missing specifications.
    """

    product = deepcopy(product)

    specifications = product.get(
        "specifications",
        {}
    )

    if not isinstance(specifications, dict):
        specifications = {}

    product["specifications"] = specifications

    # -----------------------------------------------------
    # PROCESSOR
    # -----------------------------------------------------

    processor = specifications.get(
        "processor",
        {}
    )

    if isinstance(processor, dict):

        processor_name = processor.get("name")

        if processor_name and not product.get("processor"):
            product["processor"] = processor_name

    elif isinstance(processor, str):

        if processor and not product.get("processor"):
            product["processor"] = processor

    # -----------------------------------------------------
    # MEMORY / RAM
    # -----------------------------------------------------

    memory = specifications.get(
        "memory",
        {}
    )

    if isinstance(memory, dict):

        ram_gb = memory.get("ram_gb")

        if ram_gb is not None and not product.get("ram"):

            product["ram"] = f"{ram_gb}GB"

        ram_type = memory.get("type")

        if ram_type:
            product["ram_type"] = ram_type

    # -----------------------------------------------------
    # STORAGE
    # -----------------------------------------------------

    storage = specifications.get(
        "storage",
        {}
    )

    if isinstance(storage, dict):

        capacity_gb = storage.get("capacity_gb")
        storage_type = storage.get("type")

        if capacity_gb is not None and not product.get("storage"):

            product["storage"] = (
                f"{capacity_gb}GB"
                + (
                    f" {storage_type}"
                    if storage_type
                    else ""
                )
            )

        if storage_type:
            product["storage_type"] = storage_type

    # -----------------------------------------------------
    # GRAPHICS
    # -----------------------------------------------------

    graphics = specifications.get(
        "graphics",
        {}
    )

    if isinstance(graphics, dict):

        graphics_name = graphics.get("name")

        if graphics_name and not product.get("graphics"):
            product["graphics"] = graphics_name

    elif isinstance(graphics, str):

        if graphics and not product.get("graphics"):
            product["graphics"] = graphics

    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    display = specifications.get(
        "display",
        {}
    )

    if isinstance(display, dict):

        resolution = display.get("resolution")
        refresh_rate = display.get("refresh_rate_hz")

        if resolution and not product.get("display"):
            product["display"] = resolution

        if refresh_rate is not None:
            product["refresh_rate_hz"] = refresh_rate

    elif isinstance(display, str):

        if display and not product.get("display"):
            product["display"] = display

    # -----------------------------------------------------
    # BATTERY
    # -----------------------------------------------------

    battery = specifications.get(
        "battery",
        {}
    )

    if isinstance(battery, dict):

        battery_life = battery.get("life")

        if battery_life and not product.get("battery"):
            product["battery"] = battery_life

        battery_capacity = battery.get("capacity")

        if battery_capacity is not None:
            product["battery_capacity"] = battery_capacity

    elif isinstance(battery, str):

        if battery and not product.get("battery"):
            product["battery"] = battery

    return product


# =========================================================
# PRODUCT NORMALIZATION
# =========================================================

def normalize_product(product):
    """
    Prepares a valid product for use by CommerceAI.

    Existing fields remain available.
    Structured specifications are exposed through
    backward-compatible top-level fields.
    """

    normalized = normalize_product_specifications(product)

    normalized["category"] = normalize_category(
        normalized.get("category")
    )

    if not isinstance(normalized.get("features"), list):
        if isinstance(normalized.get("features"), str):
            normalized["features"] = [
                normalized["features"]
            ]
        else:
            normalized["features"] = []

    if not isinstance(normalized.get("tags"), list):
        if isinstance(normalized.get("tags"), str):
            normalized["tags"] = [
                normalized["tags"]
            ]
        else:
            normalized["tags"] = []

    return normalized


# =========================================================
# LOAD PRODUCTS
# =========================================================

def load_products():
    """
    Loads products from the local JSON catalogue.

    Invalid individual records are skipped.
    Existing function interface is preserved.
    """

    try:

        with open(
            PRODUCT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            products = json.load(file)

            if not isinstance(products, list):

                print(
                    "Product database error: Expected a list."
                )

                return []

            valid_products = []

            for index, product in enumerate(products):

                if not validate_product(product):

                    print(
                        f"Skipping invalid product record at index {index}."
                    )

                    continue

                normalized_product = normalize_product(
                    product
                )

                valid_products.append(
                    normalized_product
                )

            return valid_products

    except FileNotFoundError:

        print(
            "Product database error: products.json was not found:",
            PRODUCT_FILE
        )

        return []

    except json.JSONDecodeError as error:

        print(
            "Product database JSON error:",
            error
        )

        return []

    except Exception as error:

        print(
            "Product database error:",
            error
        )

        return []


# =========================================================
# SEARCH PRODUCTS
# =========================================================

def search_products(
    category=None,
    budget=None
):
    """
    Searches products using category, budget and stock.

    Existing function interface is preserved.
    """

    products = load_products()

    results = []

    # -----------------------------------------------------
    # NORMALIZE BUDGET
    # -----------------------------------------------------

    if budget is not None:

        try:

            budget = float(budget)

            if budget < 0:
                return []

        except (ValueError, TypeError):

            return []

    # -----------------------------------------------------
    # FILTER PRODUCTS
    # -----------------------------------------------------

    for product in products:

        if not isinstance(product, dict):
            continue

        # -------------------------------------------------
        # CATEGORY FILTER
        # -------------------------------------------------

        if category:

            if not category_matches(
                product.get("category"),
                category
            ):
                continue

        # -------------------------------------------------
        # BUDGET FILTER
        # -------------------------------------------------

        if budget is not None:

            try:

                price = float(
                    product.get("price")
                )

            except (ValueError, TypeError):

                continue

            if price > budget:
                continue

        # -------------------------------------------------
        # STOCK FILTER
        # -------------------------------------------------

        if not product.get("stock", False):
            continue

        results.append(product)

    # -----------------------------------------------------
    # SORT BY RATING
    # -----------------------------------------------------

    def safe_rating(product):

        try:

            rating = float(
                product.get("rating") or 0
            )

            return rating

        except (ValueError, TypeError):

            return 0

    results.sort(
        key=safe_rating,
        reverse=True
    )

    return results
