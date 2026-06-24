"""Модуль валидации данных на клиенте"""

from typing import List, Dict, Any
import re


def validate_employee_data(data: Dict[str, Any]) -> List[str]:
    """
    Валидация данных сотрудника

    Args:
        data: Словарь с данными сотрудника

    Returns:
        Список ошибок (пустой если валидация пройдена)
    """
    errors = []

    # Обязательные поля
    if not data.get('last_name', '').strip():
        errors.append("Фамилия обязательна для заполнения")

    if not data.get('first_name', '').strip():
        errors.append("Имя обязательно для заполнения")

    if not data.get('position_name', '').strip():
        errors.append("Должность обязательна для заполнения")

    if not data.get('organization_id'):
        errors.append("Организация обязательна для заполнения")

    # Валидация email
    email = data.get('email', '').strip()
    if email:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            errors.append("Некорректный формат email")

    # Валидация телефона
    phone = data.get('phone_number', '').strip()
    if phone:
        phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
        if not phone_clean.isdigit():
            errors.append("Некорректный формат телефона")
        elif len(phone_clean) < 7:
            errors.append("Слишком короткий номер телефона")

    return errors


def validate_organization_data(data: Dict[str, Any]) -> List[str]:
    """
    Валидация данных организации

    Args:
        data: Словарь с данными организации

    Returns:
        Список ошибок
    """
    errors = []

    if not data.get('name', '').strip():
        errors.append("Название организации обязательно")

    if not data.get('unp', '').strip():
        errors.append("УНП обязателен")
    elif len(data['unp']) != 9:
        errors.append("УНП должен содержать 9 цифр")
    elif not data['unp'].isdigit():
        errors.append("УНП должен содержать только цифры")

    return errors


def validate_department_data(data: Dict[str, Any]) -> List[str]:
    """
    Валидация данных подразделения

    Args:
        data: Словарь с данными подразделения

    Returns:
        Список ошибок
    """
    errors = []

    if not data.get('name', '').strip():
        errors.append("Название подразделения обязательно")

    if not data.get('organization_id'):
        errors.append("Организация обязательна")

    return errors


def validate_phone_number(phone: str) -> bool:
    """Проверка корректности номера телефона"""
    if not phone:
        return True
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    return phone_clean.isdigit() and len(phone_clean) >= 7


def validate_email(email: str) -> bool:
    """Проверка корректности email"""
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))