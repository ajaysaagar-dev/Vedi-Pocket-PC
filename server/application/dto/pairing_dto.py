"""Pairing DTOs."""
from __future__ import annotations
from pydantic import BaseModel

class PairRequest(BaseModel):
    pin: str = ""

class PairResponse(BaseModel):
    token: str
    status: str
