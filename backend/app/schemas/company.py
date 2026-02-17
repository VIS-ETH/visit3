from pydantic import BaseModel


class CreateCompanyRequest(BaseModel):
	name: str
