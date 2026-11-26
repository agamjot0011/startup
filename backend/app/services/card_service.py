# Card and loop service

from app.db.session import SessionLocal


def get_card(card_id: str):
    """
    Get a card by ID.
    """
    return {"card_id": card_id, "status": "available", "row_version": 1}


def acknowledge_card(card_id: str):
    """
    Acknowledge a card.
    """
    return {"card_id": card_id, "acknowledged": True}


def start_card(card_id: str):
    """
    Start a card.
    """
    return {"card_id": card_id, "status": "in_progress", "owner": "synthetic"}


def record_result(card_id: str, result_code: str):
    """
    Record a card result.
    """
    return {"card_id": card_id, "result_code": result_code, "recorded": True}
