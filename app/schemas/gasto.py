from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, model_validator

MONTO_MAXIMO = 1_000_000


def _maximo_dos_decimales(valor: float) -> float:
    if Decimal(str(valor)).as_tuple().exponent < -2:
        raise ValueError("El monto admite como máximo 2 decimales")
    return valor


def _no_futura(valor: date) -> date:
    if valor > date.today():
        raise ValueError("La fecha no puede ser futura")
    return valor


# Solo lo nuevo de 002 vive aquí. Las reglas que ya eran de negocio en 001 (descripción
# vacía, monto <= 0, categoría inválida) siguen en services/ y responden 400 (contrato 001).
Descripcion = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Monto = Annotated[float, Field(le=MONTO_MAXIMO), AfterValidator(_maximo_dos_decimales)]
FechaNoFutura = Annotated[date, AfterValidator(_no_futura)]


class GastoCreate(BaseModel):
    # Contrato 001 (caso de error 5): campos desconocidos como usuario_id se IGNORAN al crear;
    # el dueño siempre sale del JWT. extra="forbid" aplica a PUT/PATCH y a los cuerpos nuevos.
    descripcion: Descripcion
    monto: Monto
    categoria: str
    fecha: FechaNoFutura | None = None


class GastoResponse(BaseModel):
    id: int
    descripcion: str
    monto: float
    categoria: str
    # Opcional solo para tolerar dobles de 001 cuyos dicts no la traen; el repository real siempre la devuelve.
    fecha: date | None = None

    model_config = ConfigDict(from_attributes=True)


class GastoUpdate(BaseModel):
    """PUT: reemplazo completo, los cuatro campos son obligatorios."""

    model_config = ConfigDict(extra="forbid")

    descripcion: Descripcion
    monto: Monto
    categoria: str
    fecha: FechaNoFutura


class GastoPatch(BaseModel):
    """PATCH: parcial; al menos un campo y ninguno en null explícito."""

    model_config = ConfigDict(extra="forbid")

    descripcion: Descripcion | None = None
    monto: Monto | None = None
    categoria: str | None = None
    fecha: FechaNoFutura | None = None

    @model_validator(mode="after")
    def _al_menos_un_campo_sin_null(self):
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un campo a modificar")
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Los campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


Orden = Literal["fecha", "-fecha", "monto", "-monto"]


class _RangoFechas(BaseModel):
    desde: date | None = None
    hasta: date | None = None

    @model_validator(mode="after")
    def _rango_ordenado(self):
        if self.desde and self.hasta and self.desde > self.hasta:
            raise ValueError("'desde' no puede ser posterior a 'hasta'")
        return self


class FiltrosResumen(_RangoFechas):
    pass


class FiltrosGastos(_RangoFechas):
    """Query params del listado. SIN extra="forbid": los desconocidos (p. ej. usuario_id) se
    ignoran, como exige el caso de error 5 de 001."""

    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
    categoria: str | None = None
    monto_min: float | None = None
    monto_max: float | None = None
    orden: Orden | None = None

    @model_validator(mode="after")
    def _montos_ordenados(self):
        if self.monto_min is not None and self.monto_max is not None and self.monto_min > self.monto_max:
            raise ValueError("'monto_min' no puede ser mayor que 'monto_max'")
        return self


class ResumenCategoria(BaseModel):
    categoria: str
    total: float
    cantidad: int
    disponible: float


class ResumenGastos(BaseModel):
    categorias: list[ResumenCategoria]
    total_general: float


class CategoriasResponse(BaseModel):
    categorias: list[str]
    limite_por_categoria: float
