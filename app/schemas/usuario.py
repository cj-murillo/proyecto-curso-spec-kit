from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Password = Annotated[str, Field(min_length=8, max_length=72)]


def _en_minusculas(email: str) -> str:
    return email.lower()


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: Password

    _email_en_minusculas = field_validator("email")(_en_minusculas)


class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UsuarioEmailUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password_actual: str

    _email_en_minusculas = field_validator("email")(_en_minusculas)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: str
    password_nueva: Password


class CuentaDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: str


class EmailActualizadoResponse(BaseModel):
    id: int
    email: EmailStr
    access_token: str
    token_type: str = "bearer"
