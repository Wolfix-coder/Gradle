from dataclasses import dataclass
from datetime import datetime

@dataclass
class Payments:
    id_operation: int
    ID_order: str   # Не міняти !!!
    client_id: str
    status: int
    created_at: datetime
    paid_at: datetime   
    price: float = 0.0
    paid: float = 0.0