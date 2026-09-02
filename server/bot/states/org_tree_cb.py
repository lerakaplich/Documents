from typing import Optional

from aiogram.filters.callback_data import CallbackData

class OrgTreeCallback(CallbackData, prefix="ot"):
    act: str                 # "org", "dept", "emp", "sel_org", "sel_dept", "up", "done"
    org_id: Optional[int] = None
    dept_id: Optional[int] = None
    emp_id: Optional[int] = None
    role: str                # "source", "receivers", "executors"
    page: int = 1