from flask import Blueprint, request, jsonify
from backend.services.gemini_service import summarize_article

summarizer_bp = Blueprint("summarizer", __name__, url_prefix="/api/summarize")

@summarizer_bp.route("", methods=["POST"])
def summarize_text():
    """
    Summarize any long news/article text using Gemini API with chunking and NLP fallback.
    Returns: { headline, bullets (5-7 items), paragraph }
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({
            "success": False,
            "message": "Please provide some article or news text to summarize."
        }), 400

    if len(text) < 50:
        return jsonify({
            "success": False,
            "message": "Text is too short to generate a meaningful summary. Please provide at least 50 characters."
        }), 400

    try:
        summary = summarize_article(text)
        return jsonify({
            "success": True,
            "summary": summary
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Summarization failed: {str(e)}"
        }), 500
