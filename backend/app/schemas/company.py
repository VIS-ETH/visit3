from pydantic import BaseModel
from uuid import UUID


class CreateCompanyRequest(BaseModel):
	name: str


class CompanyAssignedUserResponse(BaseModel):
	id: UUID
	email: str
	first_name: str | None = None
	last_name: str | None = None
	user_confirmed: bool
	email_confirmed: bool


class CompanyWithUsersResponse(BaseModel):
	id: UUID
	name: str
	users: list[CompanyAssignedUserResponse]
