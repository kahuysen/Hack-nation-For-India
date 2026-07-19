"""Shared request validation helpers."""

from fastapi import HTTPException

from data_eng.contracts import resolve_capability


def capability_id(value: str) -> str:
    try:
        return resolve_capability(value).id
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
