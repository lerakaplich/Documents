from dataclasses import dataclass
from typing import Optional

@dataclass
class DocumentParticipantsDTO:
    sender_id: Optional[int]
    executors: list[int]
    recipients: list[int]
    delegates: list[int]

    @property
    def all_unique_ids(self) -> list[int]:
        """Возвращает уникальный список всех участников документа"""
        all_ids = set(self.executors + self.recipients + self.delegates)
        if self.sender_id:
            all_ids.add(self.sender_id)
        return list(all_ids)