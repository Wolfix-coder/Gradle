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

    def parse_at_tags(self, text) -> str: 
        """ Розділяє @ теги, додаючи пробіл між @ та іменем користувача """

        # Якщо текст порожній або не містить @
        if not text or '@' not in text:
            return text

        # Розділяємо @ та додаємо пробіл після нього
        return re.sub(r'@(\w+)', r'\1', text)

    def generate_order_info_message(self, order_id: str,
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
            client_message: str - готовий інформаційний текст - повідомлення
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
            logger.error(f"Помилка при генерації тексту повідомлення (інформація про замовлення): {e}")
            raise

    def generate_user_info_message(self, ID: int,
                                        user_name: str,
                                        user_link: str,
                                        real_full_name: str,
                                        for_father: str,
                                        education: str,
                                        course: str,
                                        edu_group: str,
                                        phone_number: str,
                                        language_code: str,
                                        created_at: str) -> str:

            """
            Генерація інформаційного повідомлення

            Args:
                ID: int - ID користувача
                user_name: str - ім'я в telegram користувача
                user_link: str - посилання на користувача
                real_full_name: str - справжнє прізвище та ім'я користувача
                for_father: str - справжнє по-батькові користувача
                education: str - місце навчання користувача
                course: str - курс користувача
                edu_group: str - назва групи користувача
                phone_number: str - теефонний номер користувача
                language_code: str - мова якою встановлений додаток користувача
                crated_at: str - дата створення запису        
            Return:
               client_message: str - готовий інформаційний текст - повідомлення
            """
            try:    
                client_message = (
                        f"--- Інформація користувача ---\n"
                        f"<b>ID:</b> {ID}\n"
                        f"<b>НІк:</b> {user_name or 'Без нікнейма'}\n"
                        f"<b>Посилання:</b> @{user_link or 'Без посилання'}\n"
                        f"<b>Ім'я та прізвище:</b> {real_full_name}\n"
                        f"<b>По батькові:</b> {for_father}\n"
                        f"<b>Навчальний заклад:</b> {education}\n"
                        f"<b>Курс:</b> {course}\n"
                        f"<b>Група:</b> {edu_group}\n"
                        f"<b>Номер телефону:</b> {phone_number}\n"
                        f"<b>Мова застосунку:</b> {language_code}\n"
                        f"<b>Акаунт створено:</b> {created_at}\n"
                        f"---------------------------"
                    )
                return client_message
            except Exception as e:
                logger.error(f"Помилка при генерації тексту повідомлення (інформація про користувача): {e}")
                raise