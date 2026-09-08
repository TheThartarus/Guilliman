"""Paquete de mixins por entidad que componen ``CaseFileService``.

Cada módulo define una clase mixin (p. ej. ``CaseFileMethods``) con la lógica
de una entidad; ``db.service.CaseFileService`` las hereda todas. Esto
mantiene el servicio modular sin cambiar su superficie pública.
"""

from __future__ import annotations
