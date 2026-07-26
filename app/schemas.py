from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: str = ""


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None
