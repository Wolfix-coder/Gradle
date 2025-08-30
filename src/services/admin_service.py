import re

from utils.logging import logger

class AdminService:
    def parse_command(self, text: str) -> dict:
        """
        Витяг параметрів та їх значень з команди.

        Args:
            text: str - текст команди (наприклад /status --all).

        Return:
            dict - словник зі всіма аргументами та їх значеннями.
        """

        args = {}

        pattern = r'-(\w+)(?:\s+([^\s-]+))?'
        matches = re.findall(pattern, text)
        
        for arg_name, arg_value in matches:
            if arg_value:  # якщо є значення (не пустий рядок)
                args[arg_name] = arg_value
            else:  # якщо тільки флаг (пустий рядок)
                args[arg_name] = True
        return args
    
    def generate_message(self, order_id: str,
                         client_id: str,
                         ID_worker: str,
                         subject: str,
                         type_work: str,
                         order_details: str,
                         price: float,
                         order_status: int,
                         payment_status: int) -> str:

        """
        Генерація інформаційного повідомлення

        Args:
            order_id: str - ID замовлення
            client_id: str - ID клієнта
            ID_worker: str - ID працівника
            subject: str - предмет
            type_work: str - тип роботи
            order_details: str - деталі замовлення
            price: float - ціна
            order_status: int - статус виконання замовлення 
            payment_status: int - статус оплати замовлення
        
        Return:
            args: str - готовий інформаційний текст - повідомлення
        """
        try:    
            client_message = (
                    f"--- Деталі замовлення ---\n"
                    f"<b>ID замовлення:</b> {order_id}\n"
                    f"<b>Від:</b> @{client_id or 'Без нікнейма'}\n"
                    f"<b>Виконавець:</b> @{ID_worker or 'Без нікнейм'}\n"
                    f"<b>Предмет:</b> {subject}\n"
                    f"<b>Тип роботи:</b> {type_work}\n"
                    f"<b>Деталі замовлення:</b> {order_details}\n"
                    f"<b>Ціна:</b> {price}\n"
                    f"<b>Статус виконання замовлення:</b> {order_status}\n"
                    f"<b>Статус оплати:</b> {payment_status}\n"
                    f"---------------------------"
                )
            return client_message
        except Exception as e:
            logger.error(f"Помилка при генерації тексту повідомлення: {e}")
            raise