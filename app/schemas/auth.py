from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints


def _normalise_email(value: str) -> str:
    return value.strip().lower()


EmailAddress = Annotated[EmailStr, AfterValidator(_normalise_email)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
NewPassword = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class RegisterRequest(BaseModel):
    # extra="forbid" means a client cannot send "role" to register as an admin.
    model_config = ConfigDict(extra="forbid")

    name: PersonName = Field(examples=["Ada Lovelace"])
    email: EmailAddress = Field(examples=["ada@example.com"])
    password: NewPassword = Field(examples=["Sup3r-secret!"], description="At least 8 characters")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailAddress = Field(examples=["user@example.com"])
    password: str = Field(min_length=1, max_length=128, examples=["User@12345"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")
