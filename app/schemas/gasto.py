from pydantic import BaseModel


class GastoCreate(BaseModel):
    descripcion: str
    monto: float
    categoria: str


class GastoResponse(BaseModel):
    id: int
    descripcion: str
    monto: float
    categoria: str

    class Config:
        from_attributes = True
