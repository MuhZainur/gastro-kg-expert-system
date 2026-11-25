"""Strict Pydantic request models for the GastroKG API."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MedicationInput(StrictModel):
    id: StrictStr
    regular: StrictBool = False


class SymptomInput(StrictModel):
    id: StrictStr
    answer: Literal["yes", "no"]
    certainty: Decimal

    @field_validator("certainty", mode="before")
    @classmethod
    def check_certainty(cls, value: object) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ValueError("Certainty must be a number between 0.1 and 1.0.")
        dec = Decimal(str(value))
        if dec < Decimal("0.1") or dec > Decimal("1.0"):
            raise ValueError("Certainty must be between 0.1 and 1.0.")
        quantized = dec.quantize(Decimal("0.1"))
        if dec != quantized:
            raise ValueError("Certainty must have at most one decimal place.")
        return quantized


class ConsultationRequest(StrictModel):
    age: StrictInt = Field(ge=0, le=120)
    riskFactors: list[StrictStr] = Field(default_factory=list)
    medications: list[MedicationInput] = Field(default_factory=list)
    symptoms: list[SymptomInput] = Field(min_length=1, max_length=22)
    disabledRules: list[StrictStr] = Field(default_factory=list)
    extraKnowledge: StrictStr | None = None

    @field_validator("riskFactors", "disabledRules")
    @classmethod
    def check_unique_strings(cls, items: list[StrictStr]) -> list[StrictStr]:
        if len(set(items)) != len(items):
            raise ValueError("Duplicate entries are not allowed.")
        return items

    @field_validator("symptoms")
    @classmethod
    def check_unique_symptoms(cls, items: list[SymptomInput]) -> list[SymptomInput]:
        ids = [item.id for item in items]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate symptom ids are not allowed.")
        return items

    @field_validator("medications")
    @classmethod
    def check_unique_medications(cls, items: list[MedicationInput]) -> list[MedicationInput]:
        ids = [item.id for item in items]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate medication ids are not allowed.")
        return items
