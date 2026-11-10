from flask import Blueprint, request, jsonify

from services.ai_service import generate_response


# =========================================================
# CREATE CHAT BLUEPRINT
# =========================================================

chat_bp = Blueprint(
    "chat",
    __name__
)


# =========================================================
# CHAT API
# =========================================================

@chat_bp.route(
    "/api/chat",
    methods=["POST"]
)
def chat():

    # =====================================================
    # GET REQUEST DATA
    # =====================================================

    data = request.get_json()

    if not data:

        return jsonify({

            "success":
                False,

            "error":
                "Request body is missing."

        }), 400

    # =====================================================
    # GET USER MESSAGE
    # =====================================================

    message = data.get(
        "message",
        ""
    ).strip()

    if not message:

        return jsonify({

            "success":
                False,

            "error":
                "Message cannot be empty."

        }), 400

    # =====================================================
    # GET PREVIOUS SHOPPING CONTEXT
    # =====================================================

    previous_context = data.get(
        "previous_context",
        {}
    )

    if not isinstance(
        previous_context,
        dict
    ):

        previous_context = {}

    # =====================================================
    # GET PREVIOUS RECOMMENDED PRODUCTS
    # =====================================================

    previous_products = data.get(
        "previous_products",
        []
    )

    if not isinstance(
        previous_products,
        list
    ):

        previous_products = []

    # =====================================================
    # CALL AI SERVICE
    # =====================================================

    response = generate_response(

        message,

        previous_context,

        previous_products

    )

    # =====================================================
    # GET PRODUCTS
    # =====================================================

    products = response.get(
        "products",
        []
    )

    # =====================================================
    # RETURN RESPONSE TO FRONTEND
    # =====================================================

    return jsonify({

        "success":
            True,

        # -----------------------------------------------
        # Original user message
        # -----------------------------------------------

        "user_message":
            message,

        # -----------------------------------------------
        # AI response
        # -----------------------------------------------

        "response":
            response.get(
                "message",
                ""
            ),

        # -----------------------------------------------
        # Commerce information
        # -----------------------------------------------

        "type":
            response.get(
                "type"
            ),

        "intent":
            response.get(
                "intent"
            ),

        "category":
            response.get(
                "category"
            ),

        "budget":
            response.get(
                "budget"
            ),

        "purpose":
            response.get(
                "purpose"
            ),

        "preferences":
            response.get(
                "preferences",
                []
            ),

        # -----------------------------------------------
        # PRODUCT SEARCH RESULTS
        # -----------------------------------------------

        "products":
            products

    })