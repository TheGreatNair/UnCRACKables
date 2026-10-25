from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ReviewStatus = Literal["not_reviewed", "in_review", "verified", "rejected"]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=100)
    sector: str = Field(min_length=1, max_length=120)
    report_type: str = Field(alias="type", min_length=1, max_length=120)
    notes: str = Field(default="", max_length=20_000)
    timestamp: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    location_source: Literal["gps", "preset", "manual"] | None = Field(
        default=None, alias="locationSource"
    )
    location_name: str | None = Field(default=None, max_length=200, alias="locationName")
    # Accepted only for old mobile clients. Neither value is used as authority.
    sync_status: Literal["pending", "synced"] | None = Field(default=None, alias="syncStatus")
    # Compatibility-only mobile value. It is ignored; review state is server-owned.
    review_status: Literal["not_reviewed"] | None = Field(default=None, alias="reviewStatus")

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_location(self) -> "ReportCreate":
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        if has_latitude != has_longitude:
            raise ValueError("latitude and longitude must be provided together")
        if self.location_source == "gps" and not (has_latitude and has_longitude):
            raise ValueError("GPS reports require both coordinates")
        return self


class ReportResponse(BaseModel):
    id: str
    sector: str
    type: str
    notes: str
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None
    locationSource: Literal["gps", "preset", "manual"] | None = None
    locationName: str | None = None
    createdAt: datetime
    receivedAt: datetime
    syncStatus: Literal["synced"] = "synced"
    reviewStatus: ReviewStatus = "not_reviewed"
    reviewNotes: str | None = None


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, str_strip_whitespace=True)

    review_status: Literal["in_review", "verified", "rejected"] = Field(alias="reviewStatus")
    review_notes: str | None = Field(default=None, alias="reviewNotes", max_length=10_000)


class ReviewerScopeResponse(BaseModel):
    subject: str
    sector: str
    grantedBy: str
    grantedAt: datetime


class AuditEventResponse(BaseModel):
    id: str
    actorSubject: str
    action: str
    resourceType: str
    resourceId: str
    createdAt: datetime
    metadata: dict
