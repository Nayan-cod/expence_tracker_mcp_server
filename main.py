from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json

from database import get_db
from models import ExpenseCreate, ExpenseEdit, CreditCreate, BudgetCreate

app = FastAPI(title="Expense Tracker")

CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

# Note: Authentication is handled at the network level by FastMCP Cloud (Bearer Token).
# The user_id is passed natively as a standard MCP tool argument by Claude.

@app.post("/expenses")
def add_expense(expense: ExpenseCreate, user_id: str):
    """Add a new expense for a specific user_id"""
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
def edit_expense(expense_id: int, expense: ExpenseEdit, user_id: str):
    """Edit an existing expense for a specific user_id"""
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
def delete_expense(expense_id: int, user_id: str):
    """Delete an expense for a specific user_id"""
    with get_db() as conn:
        with conn.cursor() as c:
            c.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s", (expense_id, user_id))
            deleted = c.rowcount > 0
        conn.commit()
        if deleted:
            return {"status": "ok", "message": f"Expense {expense_id} deleted"}
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found or you don't have permission")

@app.get("/expenses")
def list_expenses(start_date: str, end_date: str, user_id: str):
    """List expenses within a date range for a specific user_id"""
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
def add_credit(credit: CreditCreate, user_id: str):
    """Add a credit source for a specific user_id"""
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
def add_budget(budget: BudgetCreate, user_id: str):
    """Add a budget for a category for a specific user_id"""
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
def summarize(start_date: str, end_date: str, user_id: str, category: Optional[str] = None):
    """Summarize expenses by category for a specific user_id"""
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
def get_categories():
    """Get the standard list of categories"""
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)