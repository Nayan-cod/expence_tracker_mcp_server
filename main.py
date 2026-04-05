from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json

from database import get_db
from models import ExpenseCreate, ExpenseEdit, CreditCreate, BudgetCreate

app = FastAPI(title="Expense Tracker")

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

# Define API Key security scheme
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_current_user(api_key: str = Security(api_key_header)) -> str:
    """
    Validate the API key and return a user identifier.
    For simplicity, we use the API key itself as the user_id.
    In a production system, this would lookup the user in the database.
    """
    if not api_key:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    # For now, treat API key as user identifier
    return api_key

@app.post("/expenses")
def add_expense(expense: ExpenseCreate, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO expenses(user_id, date, amount, category, subcategory, note) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (user_id, expense.date, expense.amount, expense.category, expense.subcategory, expense.note)
            )
            row_id = c.fetchone()["id"]
        conn.commit()
        return {"status": "ok", "id": row_id}

@app.put("/expenses/{expense_id}")
def edit_expense(expense_id: int, expense: ExpenseEdit, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
            if not c.fetchone():
                raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found or you don't have permission")
            
            updates = []
            params = []
            if expense.date is not None:
                updates.append("date = %s")
                params.append(expense.date)
            if expense.amount is not None:
                updates.append("amount = %s")
                params.append(expense.amount)
            if expense.category is not None:
                updates.append("category = %s")
                params.append(expense.category)
            if expense.subcategory is not None:
                updates.append("subcategory = %s")
                params.append(expense.subcategory)
            if expense.note is not None:
                updates.append("note = %s")
                params.append(expense.note)
                
            if not updates:
                return {"status": "error", "message": "No fields to update provided"}
                
            params.extend([expense_id, user_id])
            c.execute(f"UPDATE expenses SET {', '.join(updates)} WHERE id = %s AND user_id = %s", params)
        conn.commit()
        return {"status": "ok", "message": f"Expense {expense_id} updated"}

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
            deleted = c.rowcount > 0
        conn.commit()
        if deleted:
            return {"status": "ok", "message": f"Expense {expense_id} deleted"}
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found or you don't have permission")

@app.get("/expenses")
def list_expenses(start_date: str, end_date: str, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE user_id = %s AND date BETWEEN %s AND %s
                ORDER BY id ASC
                """,
                (user_id, start_date, end_date)
            )
            return [dict(r) for r in c.fetchall()]

@app.post("/credits")
def add_credit(credit: CreditCreate, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO credits(user_id, date, amount, source, note) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (user_id, credit.date, credit.amount, credit.source, credit.note)
            )
            row_id = c.fetchone()["id"]
        conn.commit()
        return {"status": "ok", "id": row_id}

@app.post("/budgets")
def add_budget(budget: BudgetCreate, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute(
                """
                INSERT INTO budgets(user_id, month, category, amount) 
                VALUES (%s,%s,%s,%s)
                ON CONFLICT(user_id, month, category) DO UPDATE SET amount=EXCLUDED.amount
                """,
                (user_id, budget.month, budget.category, budget.amount)
            )
        conn.commit()
        return {"status": "ok"}

@app.get("/summary")
def summarize(start_date: str, end_date: str, category: Optional[str] = None, user_id: str = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as c:
            query = (
                """
                SELECT category, SUM(amount) AS total_amount
                FROM expenses
                WHERE user_id = %s AND date BETWEEN %s AND %s
                """
            )
            params = [user_id, start_date, end_date]

            if category:
                query += " AND category = %s"
                params.append(category)

            query += " GROUP BY category ORDER BY category ASC"

            c.execute(query, params)
            return [dict(r) for r in c.fetchall()]

@app.get("/categories")
def get_categories(user_id: str = Depends(get_current_user)):
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)