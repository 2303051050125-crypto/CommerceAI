
from itertools import product

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os

from services.product_service import load_products


purchase_bp = Blueprint("purchase", __name__)


# =========================================================
# PURCHASE DATABASE
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

PURCHASE_FILE = os.path.join(
    BASE_DIR,
    "database",
    "purchases.json"
)


# =========================================================
# LOAD PURCHASES
# =========================================================

def load_purchases():
    try:
        with open(PURCHASE_FILE, "r", encoding="utf-8") as file:
            purchases = json.load(file)

        if not isinstance(purchases, list):
            raise ValueError("Purchase database must contain a JSON list.")

        return purchases

    except FileNotFoundError:
        return []

    except (json.JSONDecodeError, ValueError) as error:
        print("Purchase database error:", error)
        raise RuntimeError(
            "Purchase history is corrupted. Please check purchases.json."
        ) from error

    except OSError as error:
        print("Purchase database error:", error)
        raise RuntimeError(
            "Unable to read purchase history."
        ) from error

# =========================================================
# SAVE PURCHASES
# =========================================================

def save_purchases(purchases):
    try:
        os.makedirs(
            os.path.dirname(PURCHASE_FILE),
            exist_ok=True
        )

        with open(PURCHASE_FILE, "w", encoding="utf-8") as file:
            json.dump(
                purchases,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as error:
        print("Purchase save error:", error)
        return False


# =========================================================
# CREATE PURCHASE
# =========================================================

@purchase_bp.route("/api/purchase", methods=["POST"])
def create_purchase():

    data = request.get_json(silent=True)

    # -----------------------------------------------------
    # CHECK REQUEST
    # -----------------------------------------------------

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "A valid JSON request body is required."
        }), 400

    product_id = data.get("product_id")

    if product_id is None or str(product_id).strip() == "":
        return jsonify({
            "success": False,
            "error": "Product ID is required."
        }), 400

    # -----------------------------------------------------
    # VALIDATE QUANTITY
    # -----------------------------------------------------

    quantity = data.get("quantity", 1)

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or quantity < 1
    ):
        return jsonify({
            "success": False,
            "error": "Quantity must be a positive whole number."
        }), 400

    # -----------------------------------------------------
    # GET TRUSTED PRODUCT INFORMATION
    # -----------------------------------------------------

    products = load_products()

    product = next(
        (
            item for item in products
            if str(item.get("id")) == str(product_id)
        ),
        None
    )

    if product is None:
        return jsonify({
            "success": False,
            "error": "Product not found in the catalogue."
        }), 404
# -----------------------------------------------------
# CHECK PRODUCT STOCK
# -----------------------------------------------------

    if product.get("stock") is not True:
        return jsonify({
            "success": False,
            "error": "This product is currently out of stock."
        }), 409


    product_name = product.get("name")
    category = product.get("category")
    price = product.get("price")

    if (
        not product_name
        or not category
        or isinstance(price, bool)
        or not isinstance(price, (int, float))
        or price < 0
    ):
        return jsonify({
            "success": False,
            "error": "Product information in the catalogue is invalid."
        }), 500

    # -----------------------------------------------------
    # CALCULATE TRUSTED TOTAL
    # -----------------------------------------------------

    total = round(price * quantity, 2)

    # -----------------------------------------------------
    # LOAD EXISTING PURCHASES
    # -----------------------------------------------------

    try:
        purchases = load_purchases()
    except RuntimeError as error:
        return jsonify({
        "success": False,
        "error": str(error)
    }), 500

    # -----------------------------------------------------
    # GENERATE PURCHASE ID
    # -----------------------------------------------------

    numeric_ids = [
        purchase.get("purchase_id")
        for purchase in purchases
        if isinstance(purchase.get("purchase_id"), int)
        and not isinstance(purchase.get("purchase_id"), bool)
    ]

    purchase_id = max(numeric_ids, default=0) + 1

    # -----------------------------------------------------
    # CREATE PURCHASE RECORD
    # -----------------------------------------------------

    purchase = {
        "purchase_id": purchase_id,
        "product_id": product.get("id"),
        "product_name": product_name,
        "category": category,
        "price": price,
        "quantity": quantity,
        "total": total,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Purchased"
    }

    # -----------------------------------------------------
    # SAVE PURCHASE
    # -----------------------------------------------------

    purchases.append(purchase)

    if not save_purchases(purchases):
        return jsonify({
            "success": False,
            "error": "Could not save purchase."
        }), 500

    # -----------------------------------------------------
    # TERMINAL LOG
    # -----------------------------------------------------

    print()
    print("========================================")
    print("NEW PURCHASE")
    print(purchase)
    print("========================================")
    print()

    # -----------------------------------------------------
    # RETURN RESPONSE
    # -----------------------------------------------------

    return jsonify({
        "success": True,
        "message": "Purchase created successfully.",
        "purchase": purchase
    }), 201


# =========================================================
# GET PURCHASE HISTORY
# =========================================================

@purchase_bp.route("/api/purchases", methods=["GET"])
def get_purchases():

    try:
        purchases = load_purchases()

        return jsonify({
            "success": True,
            "count": len(purchases),
            "purchases": purchases
        })

    except RuntimeError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 500