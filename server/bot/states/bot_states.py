from aiogram.fsm.state import State, StatesGroup


class CreateDocumentFSM(StatesGroup):
    # Обязательный начальный базис
    waiting_for_type = State()              # Выбор типа документа
    waiting_for_direction = State()         # Выбор направления (internal / external)
    waiting_for_sequence_num = State()      # Порядковый номер
    waiting_for_reg_num = State()           # Регистрационный номер
    waiting_for_needs_response = State()    # Требуется ли ответ

    # Динамические текстовые и атрибутивные поля (управляются JSONB types.fields)
    waiting_for_title = State()             # Ввод темы (title)
    waiting_for_about = State()             # Ввод содержания / "Касается" (about)
    waiting_for_sent_date = State()         # Выбор/Ввод даты отправки (sent_date)
    waiting_for_deadline = State()          # Выбор/Ввод срока исполнения (deadline)

    # Участники и классификация (управляются JSONB types.fields)
    waiting_for_sender = State()            # Выбор/Переопределение отправителя (sender_id)
    waiting_for_recipients = State()        # Выбор получателей (recipients)
    waiting_for_executors = State()         # Выбор исполнителей (executors)
    waiting_for_tags = State()              # Выбор тегов (tag_ids)

    # Обязательный финальный базис
    waiting_for_attachments = State()       # Загрузка файлов/вложений (attachments)
    confirm_creation = State()              # Финальное подтверждение и сборка DTO