import uuid
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True,
        index=True,
        nullable=False
    )
    username: str = Field(unique=True, index=True)
    sub: str | None = Field(default=None, index=True)
    email: str = Field(unique=True)
    password: str | None
    first_name: str | None = None
    last_name: str | None = None
    
    is_confirmed: bool = False
    is_staff: bool = False
    is_admin: bool = False