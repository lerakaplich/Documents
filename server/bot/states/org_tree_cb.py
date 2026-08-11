from aiogram.filters.callback_data import CallbackData

class OrgTreeCallback(CallbackData, prefix="org_tree"):
    action: str          # "select_dept", "select_emp", "select_all_dept", "up"
    dept_id: int | None  # ID текущего или выбираемого отдела
    emp_id: int | None   # ID сотрудника (если выбран)
    target_role: str     # "sender", "recipients", "executors"