# Content service

from app.db.session import SessionLocal


def list_content_items():
    """
    List content items.
    """
    return [
        {
            "content_item_id": "synthetic",
            "semantic_key": "synthetic",
            "content_class": "home_look_for",
            "audience": "patient",
            "purpose": "safety",
        }
    ]
