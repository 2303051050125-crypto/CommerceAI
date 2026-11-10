
from recommendation_service import recommend_products


# =========================================================
# TEST PRODUCTS
# =========================================================

products = [
    {
        "id": 1,
        "name": "Programming Laptop",
        "category": "laptop",
        "price": 65000,
        "rating": 4.5,
        "reviews": 1500,
        "features": [
            "16GB RAM",
            "512GB SSD",
            "Ryzen 7"
        ],
        "tags": [
            "programming",
            "student",
            "gaming"
        ]
    },
    {
        "id": 2,
        "name": "Budget Laptop",
        "category": "laptop",
        "price": 45000,
        "rating": 4.0,
        "reviews": 500,
        "features": [
            "8GB RAM",
            "256GB SSD"
        ],
        "tags": [
            "student"
        ]
    },
    {
        "id": 3,
        "name": "Premium Gaming Laptop",
        "category": "laptop",
        "price": 90000,
        "rating": 4.8,
        "reviews": 5000,
        "features": [
            "32GB RAM",
            "1TB SSD"
        ],
        "tags": [
            "gaming",
            "programming"
        ]
    }
]


# =========================================================
# TEST 1: STRICT MINIMUM RAM REQUIREMENT
# =========================================================

print("\nTEST 1: Minimum 16GB RAM")

requirements_ram = {
    "category": "laptop",
    "preferences": [
        "at least 16GB RAM"
    ]
}

results_ram = recommend_products(
    products,
    requirements_ram,
    limit=5
)

ram_names = [
    product["name"]
    for product in results_ram
]

print("Recommended:", ram_names)

assert "Programming Laptop" in ram_names
assert "Premium Gaming Laptop" in ram_names
assert "Budget Laptop" not in ram_names

print("PASS: Products below 16GB RAM are excluded.")


# =========================================================
# TEST 2: STRICT MINIMUM STORAGE REQUIREMENT
# =========================================================

print("\nTEST 2: Minimum 512GB SSD")

requirements_storage = {
    "category": "laptop",
    "preferences": [
        "minimum 512GB SSD"
    ]
}

results_storage = recommend_products(
    products,
    requirements_storage,
    limit=5
)

storage_names = [
    product["name"]
    for product in results_storage
]

print("Recommended:", storage_names)

assert "Programming Laptop" in storage_names
assert "Premium Gaming Laptop" in storage_names
assert "Budget Laptop" not in storage_names

print("PASS: Products below 512GB storage are excluded.")


# =========================================================
# TEST 3: NORMAL PREFERENCE MUST NOT HARD-FILTER
# =========================================================

print("\nTEST 3: Prefer 16GB RAM")

requirements_preference = {
    "category": "laptop",
    "preferences": [
        "I prefer 16GB RAM"
    ]
}

results_preference = recommend_products(
    products,
    requirements_preference,
    limit=5
)

preference_names = [
    product["name"]
    for product in results_preference
]

print("Recommended:", preference_names)

assert "Budget Laptop" in preference_names
assert "Programming Laptop" in preference_names

print("PASS: Lower-RAM products remain eligible for normal preferences.")


# =========================================================
# TEST 4: NO HARDWARE REQUIREMENT
# =========================================================

print("\nTEST 4: No RAM or storage requirement")

requirements_normal = {
    "category": "laptop",
    "budget": 70000,
    "purpose": "programming gaming",
    "preferences": [
        "student"
    ]
}

results_normal = recommend_products(
    products,
    requirements_normal,
    limit=5
)

normal_names = [
    product["name"]
    for product in results_normal
]

print("Recommended:")

for product in results_normal:

    print(
        product["name"],
        "->",
        product["match_score"],
        "% Match"
    )

assert len(results_normal) == 3

print("PASS: All category-matching products remain eligible.")


# =========================================================
# FINAL RESULT
# =========================================================

print("\n========================================")
print("ALL 4 RECOMMENDATION TESTS PASSED!")
print("========================================")
