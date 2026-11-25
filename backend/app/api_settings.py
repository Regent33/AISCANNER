"""App settings (single row)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, SecretStr, StringConstraints

from . import db, provider_keys

router = APIRouter()
ModelId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256, pattern=r"^\S+$")]

class SettingsIn(BaseModel):
    provider: str | None = Field(default=None, pattern="^(local|cloud|openrouter|nvidia|mock)$")
    confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    cloud_model: str | None = None
    openrouter_model: ModelId | None = None
    nvidia_model: ModelId | None = None
    add_keys: SecretStr | None = None
    local_model: str | None = None
    watch_folder: str | None = None
    show_names: bool | None = None


@router.get("/settings")
def get_settings():
    with db.connect() as c:
        settings = db.row(c.execute("SELECT * FROM settings").fetchone())
        settings["key_counts"] = {p: len(provider_keys.keys_for(p)) for p in provider_keys.PREFIX}
        settings["saved_models"] = {p: [] for p in provider_keys.PREFIX}
        for row in c.execute("SELECT provider, model FROM provider_model ORDER BY model"):
            settings["saved_models"][row["provider"]].append(row["model"])
        return settings


@router.put("/settings")
def put_settings(s: SettingsIn):
    upd = s.model_dump(exclude_none=True, exclude={"add_keys"})
    extra = []
    if s.add_keys:
        if s.provider not in provider_keys.PREFIX:
            raise HTTPException(422, "Choose a provider before adding its keys.")
        extra = s.add_keys.get_secret_value().replace(",", " ").split()
        if any(not key.isascii() or not key.isprintable() for key in extra):
            raise HTTPException(422, "API keys must contain printable ASCII characters.")
    if s.provider in provider_keys.PREFIX and not provider_keys.keys_for(s.provider, extra):
        raise HTTPException(422, "Add at least one API key for this provider before saving.")
    with db.connect() as c:
        if upd:
            fields = ", ".join(f"{k}=?" for k in upd)
            c.execute("BEGIN IMMEDIATE")
            c.execute(f"UPDATE settings SET {fields}", tuple(upd.values()))
            for provider in provider_keys.PREFIX:
                if model := upd.get(f"{provider}_model"):
                    c.execute("INSERT OR IGNORE INTO provider_model(provider, model) VALUES (?, ?)", (provider, model))
            if extra:
                provider_keys.add_keys(s.provider, extra)
    return get_settings()

