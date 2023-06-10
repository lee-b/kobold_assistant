from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DialogEvent(ABC):
    timestamp: datetime