from typing import Optional, Dict, Any
import re

ALLOWED_COURSES = ['1', '2', '3', '4']

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