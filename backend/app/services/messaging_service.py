"""In-app messaging — handbook detailed step 20 (lines 7896-8012).

The in-app item is authoritative. A view is not an acknowledgement and never
closes a card. Messages carry approved content only, with an immutable publish
event and a separate view event.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.services.authz_service import AuthzError
from app.services.event_ledger import event_ledger
from app.services.session_service import SessionRecord
from app.services import supabase_store


class MessagingError(Exception):
    def __init__(self, code: str, status: int = 400, message: str = "") -> None:
        self.code, self.status = code, status
        self.message = message or code
        super().__init__(self.message)


@dataclass
class Message:
    message_id: str
    practice_id: str
    patient_id: str
    body: str
    published_by: str
    published_at: str
    views: list[dict] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "message_id": self.message_id,
            "patient_id": self.patient_id,
            "body": self.body,
            "published_by": self.published_by,
            "published_at": self.published_at,
            "view_count": len(self.views),
            "view_is_not_acknowledgement": True,
        }


class MessagingService:
    def __init__(self) -> None:
        self._messages: dict[str, Message] = {}
        self._lock = threading.RLock()

    def publish(self, practice_id: str, patient_id: str, body: str, actor: SessionRecord) -> Message:
        if not body.strip():
            raise MessagingError("MESSAGE_BODY_REQUIRED", 400)
        with self._lock:
            message = Message(
                message_id=str(uuid.uuid4()), practice_id=practice_id, patient_id=patient_id,
                body=body, published_by=actor.user_id,
                published_at=datetime.now(timezone.utc).isoformat(),
            )
            self._messages[message.message_id] = message
            supabase_store.save("messages", message, "message_id")
            event_ledger.append(
                practice_id=practice_id, patient_id=patient_id,
                event_type="in_app_message_published.v1", source_type="staff_message",
                source_id=message.message_id, payload={"body": body, "published_by": actor.user_id},
                actor_user_id=actor.user_id,
            )
            return message

    def get(self, message_id: str) -> Message:
        message = self._messages.get(message_id)
        if message is None:
            raise MessagingError("MESSAGE_NOT_FOUND", 404)
        return message

    def for_patient(self, practice_id: str, patient_id: str) -> list[Message]:
        return [
            m for m in self._messages.values()
            if m.practice_id == practice_id and m.patient_id == patient_id
        ]

    def view(self, message_id: str, actor: SessionRecord) -> dict:
        with self._lock:
            message = self.get(message_id)
            entry = {
                "viewer_user_id": actor.user_id,
                "viewed_at": datetime.now(timezone.utc).isoformat(),
                "is_acknowledgement": False,
            }
            message.views.append(entry)
            supabase_store.insert("message_views", {
                "message_id": message.message_id, "viewer_user_id": actor.user_id,
                "viewed_at": entry["viewed_at"], "is_acknowledgement": False,
            })
            event_ledger.append(
                practice_id=message.practice_id, patient_id=message.patient_id,
                event_type="message_viewed.v1", source_type="in_app_view",
                source_id=message.message_id, payload=entry,
                actor_user_id=actor.user_id,
            )
            return entry


messaging_service = MessagingService()
