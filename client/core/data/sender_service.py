from typing import Optional, List, Dict, Any


class SenderService:
    def __init__(self):
        self.test_senders: List[Dict[str, Any]] = []
        self._init_test_senders()

    def _init_test_senders(self):
        """Инициализация тестовых данных отправителей"""
        self.test_senders = [
            {
                'id': 1, 'type': 'employee', 'employee_id': 101,
                'last_name': 'Иванов', 'first_name': 'Иван', 'patronymic': 'Иванович',
                'position': 'Начальник отдела', 'department_id': 1,
                'department_name': 'Отдел разработки', 'department_type': 'Отдел',
                'organization_name': 'ООО "ТехноСервис"', 'display_text': 'Иванов Иван Иванович'
            },
            {
                'id': 2, 'type': 'employee', 'employee_id': 102,
                'last_name': 'Петрова', 'first_name': 'Екатерина', 'patronymic': 'Алексеевна',
                'position': 'Главный бухгалтер', 'department_id': 2,
                'department_name': 'Бухгалтерия', 'department_type': 'Отдел',
                'organization_name': 'ООО "ТехноСервис"', 'display_text': 'Петрова Екатерина Алексеевна'
            },
            {
                'id': 4, 'type': 'organization', 'organization_id': 201,
                'organization_name': 'ОАО "ЭнергоСнаб"', 'unp': '123456789',
                'display_text': 'ОАО "ЭнергоСнаб"'
            },
            {
                'id': 6, 'type': 'department', 'department_id': 1,
                'department_name': 'Отдел телематики', 'department_type': 'Отдел',
                'organization_name': 'ООО "ТехноСервис"', 'display_text': 'Отдел телематики'
            }
        ]

        # Генерируем поисковые строки для каждого отправителя
        for sender in self.test_senders:
            search_variants = [
                sender.get('display_text', ''),
                sender.get('last_name', ''),
                sender.get('first_name', ''),
                sender.get('patronymic', ''),
                sender.get('organization_name', ''),
                sender.get('department_name', ''),
            ]
            if sender.get('last_name'):
                full_name = sender['last_name']
                if sender.get('first_name'):
                    full_name += ' ' + sender['first_name'][0] + '.'
                    if sender.get('patronymic'):
                        full_name += sender['patronymic'][0] + '.'
                search_variants.append(full_name)

            sender['search_string'] = ' '.join(filter(None, search_variants))

    def get_sender_display_text(self, sender: Dict[str, Any]) -> str:
        """Получить красивый отформатированный текст для интерфейса"""
        if not sender:
            return "Неизвестный отправитель"

        sender_type = sender.get('type', '')

        if sender_type == 'employee':
            last_name = sender.get('last_name', '')
            first_initial = sender.get('first_name', '')[0] + '.' if sender.get('first_name') else ''
            patronymic_initial = sender.get('patronymic', '')[0] + '.' if sender.get('patronymic') else ''
            return f"Отправитель: {last_name} {first_initial}{patronymic_initial}"

        elif sender_type == 'organization':
            return f"Отправитель: {sender.get('organization_name', '')}"

        elif sender_type == 'department':
            dept_type = sender.get('department_type', '')
            dept_name = sender.get('department_name', '')
            if dept_type and dept_name:
                return f"Отправитель: {dept_type} {dept_name}"
            return f"Отправитель: {dept_name or 'Структурное подразделение'}"

        return f"Отправитель: {sender.get('display_text', 'Неизвестный отправитель')}"

    def try_find_sender_by_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Поиск отправителя по тексту (умный скоринг совпадений)"""
        if not text:
            return None

        text_lower = text.lower().strip()
        best_match = None
        best_score = 0

        for sender in self.test_senders:
            search_string = sender.get('search_string', '').lower()
            display_text = sender.get('display_text', '').lower()

            if text_lower in search_string or text_lower in display_text:
                score = 0
                words = text_lower.split()
                for word in words:
                    if word in search_string or word in display_text:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = sender

        return best_match