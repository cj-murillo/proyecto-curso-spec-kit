"""Dobles de prueba que cumplen el contrato de repositories/gastos.py (sin unittest.mock, Art. VII.2)."""
from datetime import date


class RepoGastosEnMemoria:
    def __init__(self):
        self.gastos: list[dict] = []
        self._siguiente_id = 1
        self.bloqueos: list[int] = []

    def sembrar(self, usuario_id, descripcion="x", monto=10.0, categoria="comida", fecha=None):
        gasto = {
            "id": self._siguiente_id,
            "descripcion": descripcion,
            "monto": monto,
            "categoria": categoria,
            "fecha": fecha or date.today(),
            "usuario_id": usuario_id,
        }
        self._siguiente_id += 1
        self.gastos.append(gasto)
        return gasto

    @staticmethod
    def _publico(g):
        return {k: v for k, v in g.items() if k != "usuario_id"}

    def bloquear_usuario(self, db, usuario_id):
        self.bloqueos.append(usuario_id)

    def guardar(self, db, usuario_id, descripcion, monto, categoria, fecha=None):
        return self._publico(self.sembrar(usuario_id, descripcion, monto, categoria, fecha))

    def obtener_por_id(self, db, gasto_id):
        return next((dict(g) for g in self.gastos if g["id"] == gasto_id), None)

    def actualizar(self, db, gasto_id, usuario_id, descripcion, monto, categoria, fecha):
        for g in self.gastos:
            if g["id"] == gasto_id and g["usuario_id"] == usuario_id:
                g.update(descripcion=descripcion, monto=monto, categoria=categoria, fecha=fecha)
                return self._publico(g)
        return None

    def eliminar(self, db, gasto_id, usuario_id):
        antes = len(self.gastos)
        self.gastos = [
            g for g in self.gastos if not (g["id"] == gasto_id and g["usuario_id"] == usuario_id)
        ]
        return len(self.gastos) < antes

    def total_por_categoria(self, db, usuario_id, categoria, excluir_id=None):
        return float(
            sum(
                g["monto"]
                for g in self.gastos
                if g["usuario_id"] == usuario_id
                and g["categoria"] == categoria
                and g["id"] != excluir_id
            )
        )

    def _filtrar(self, usuario_id, categoria=None, desde=None, hasta=None, monto_min=None, monto_max=None):
        return [
            g for g in self.gastos
            if g["usuario_id"] == usuario_id
            and (categoria is None or g["categoria"] == categoria)
            and (desde is None or g["fecha"] >= desde)
            and (hasta is None or g["fecha"] <= hasta)
            and (monto_min is None or g["monto"] >= monto_min)
            and (monto_max is None or g["monto"] <= monto_max)
        ]

    def listar(self, db, usuario_id, skip=0, limit=20, orden=None, **filtros):
        self.ultimo_listar = {"orden": orden, **filtros}
        gastos = sorted(self._filtrar(usuario_id, **filtros), key=lambda g: g["id"])
        if orden:
            campo = orden.lstrip("-")
            gastos = sorted(gastos, key=lambda g: g[campo], reverse=orden.startswith("-"))
        return [self._publico(g) for g in gastos[skip : skip + limit]]

    def contar(self, db, usuario_id, **filtros):
        return len(self._filtrar(usuario_id, **filtros))

    def resumen_por_categoria(self, db, usuario_id, desde=None, hasta=None):
        filas = {}
        for g in self._filtrar(usuario_id, desde=desde, hasta=hasta):
            f = filas.setdefault(g["categoria"], {"categoria": g["categoria"], "total": 0.0, "cantidad": 0})
            f["total"] += g["monto"]
            f["cantidad"] += 1
        return list(filas.values())
