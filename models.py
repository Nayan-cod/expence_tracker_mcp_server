from pydantic import BaseModel
from typing import Optional

class ExpenseCreate(BaseModel):
    date: str
    amount: float
    category: str
    subcategory: str = ""
    note: str = ""

class ExpenseEdit(BaseModel):
    date: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    note: Optional[str] = None

class CreditCreate(BaseModel):
    date: str
    amount: float
    source: str
    note: str = ""

class BudgetCreate(BaseModel):
    month: str
    category: str
    amount: float
