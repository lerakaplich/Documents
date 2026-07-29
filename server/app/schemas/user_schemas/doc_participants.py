from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DocumentParticipantsDTO:
    sender_id: Optional[int]
    executors: List[int]
    recipients: List[int]
    delegates: List[int]

    @property
    def all_unique_ids(self) -> List[int]:
        """Возвращает уникальный список всех участников документа"""
        all_ids = set(self.executors + self.recipients + self.delegates)
        if self.sender_id:
            all_ids.add(self.sender_id)
        return list(all_ids)