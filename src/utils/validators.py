from typing import Optional, Dict, Any
import re

ALLOWED_COURSES = ['1', '2', '3', '4']

ALLOWED_TABLES = {
    'user_data': ['ID', 'user_name', 'user_link', 'real_full_name', 'for_father', 'education', 'course', 'edu_group', 'phone_number', 'language_code', 'created_at'],
    'request_order': ['ID_order', 'ID_user', 'ID_worker', 'subject', 'type_work', 'order_details', 'status', 'created_at', 'taken_at', 'completed_at', 'updated_at'],
    'payments': ['id_operation', 'ID_order', 'status', 'price', 'paid', 'created_at', 'paid_at']

}

# Функції валідації
def validate_input(text: str, max_length: int) -> Optional[str]:
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) == 0 or len(text) > max_length:
        return None
    text = re.sub(r'[<>\'"]', '', text)
    return text

def validate_course(course: str) -> bool:
    return course in ALLOWED_COURSES

def _validate_table_column(table: str, column: str):
        if table not in ALLOWED_TABLES:
            raise ValueError(f"❌ Таблиця '{table}' не дозволена")
        
        if column not in ALLOWED_TABLES[table]:
            raise ValueError(f"❌ Колонка '{column}' не існує в таблиці '{table}'")