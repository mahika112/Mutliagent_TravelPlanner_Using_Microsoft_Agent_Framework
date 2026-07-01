from pydantic import BaseModel, Field, field_validator
from typing import Literal

VALID_STYLES = ("budget", "mid-range", "luxury")


class TripPlan(BaseModel):
    """
    Validated input model for a travel planning request.

    Used by main.py to normalise CLI/interactive input before
    handing it to PlannerAgent.
    """

    city: str = Field(
        description="Destination city, e.g. 'Tokyo' or 'Paris,FR'."
    )
    days: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Trip duration in days (1–30).",
    )
    travel_style: Literal["budget", "mid-range", "luxury"] = Field(
        default="mid-range",
        description="Spending level: 'budget', 'mid-range', or 'luxury'.",
    )
    interests: str = Field(
        default="",
        description=(
            "Comma-separated interests passed to PlacesAgent, "
            "e.g. 'anime, food, history'. Empty string means no filter."
        ),
    )

    @field_validator("city")
    @classmethod
    def city_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("City must not be empty.")
        return v

    @field_validator("interests")
    @classmethod
    def clean_interests(cls, v: str) -> str:
        # Normalise: strip whitespace around each interest
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return ", ".join(parts)