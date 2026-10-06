import hashlib, time
from fastapi import HTTPException
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import case
from app.database.db import SessionLocal
from app.models.account_security import RequestBudget

def consume(key, limit, seconds, weight=1):
    window = int(time.time()) // seconds
    key = hashlib.sha256(key.encode()).hexdigest()
    with SessionLocal() as db:
        statement = insert(RequestBudget).values(key=key, window=window, count=weight)
        statement = statement.on_conflict_do_update(index_elements=['key'], set_={
            'window': window,
            'count': case((RequestBudget.window == window, RequestBudget.count + weight), else_=weight)})
        db.execute(statement)
        row = db.get(RequestBudget, key)
        count = row.count
        db.commit()
    if count > limit:
        raise HTTPException(429, 'Too many requests. Please try again later.', headers={'Retry-After': str(seconds)})
