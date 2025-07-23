from dataclasses import dataclass
from datetime import datetime

@dataclass
class Payments:
    id_operation: int
    ID_order: str   # Не міняти !!!
    ID_worker: str
    ID_user: str
    subject: str
    type_work: int
    order_details: str
    status: int
    created_at: datetime
    paid_at: datetime   
    price: float = 0.0
    paid: float = 0.0