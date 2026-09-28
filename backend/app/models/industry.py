from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base import BaseEntity, BaseLink, unique_among_active_index

if TYPE_CHECKING:
    from app.models.company import KpCompanyProfile
    from app.models.kp_event import KpBookingCompanyDetailsIndustryLink


class Industry(BaseEntity, table=True):
    __table_args__ = (unique_among_active_index("ix_industry_name", "name"),)

    name: str = Field(min_length=1)

    profile_links: list["KpCompanyProfileIndustryLink"] = Relationship(
        back_populates="industry"
    )
    snapshot_links: list["KpBookingCompanyDetailsIndustryLink"] = Relationship(
        back_populates="industry"
    )


class KpCompanyProfileIndustryLink(BaseLink, table=True):
    profile_id: UUID = Field(foreign_key="kpcompanyprofile.id", primary_key=True)
    industry_id: UUID = Field(foreign_key="industry.id", primary_key=True)

    profile: "KpCompanyProfile" = Relationship(back_populates="industry_links")
    industry: Industry = Relationship(back_populates="profile_links")
