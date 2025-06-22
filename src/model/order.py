from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class OrderStatus(Enum):
    NEW = 1 # замовлення створено
    IN_PROGRESS = 2 # замовлення виконується
    COMPLETED = 3 # замовлення виконано
    CANCELLED = 4 # замовлення скасовано
    PENDING_CONFIRMATION = 5 

@dataclass
class Order:
    ID_order: str
    ID_user: int
    user_name: str
    user_link: str
    subject: str
    type_work: str
    order_details: str
    status: OrderStatus = OrderStatus.NEW
    ID_worker: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    taken_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_price: float = 0.0
    paid_amount: float = 0.0

    @property
    def is_completed(self) -> bool:
        return self.status == OrderStatus.COMPLETED

    @property
    def is_in_progress(self) -> bool:
        return self.status == OrderStatus.IN_PROGRESS

    @property
    def is_paid(self) -> bool:
        return self.paid_amount >= self.total_price

    def update_status(self, new_status: OrderStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.now()
        if new_status == OrderStatus.COMPLETED:
            self.completed_at = datetime.now()

    def assign_worker(self, worker_id: int) -> None:
        self.ID_worker = worker_id
        self.status = OrderStatus.IN_PROGRESS
        self.taken_at = datetime.now()
        self.updated_at = datetime.now()

    def add_payment(self, amount: float) -> None:
        self.paid_amount += amount
        self.updated_at = datetime.now()