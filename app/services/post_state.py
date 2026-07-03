class PostStateService:
    """Contrato de transiciones de estado de Post. Implementacion: Spec 4 (P5).

    Reglas acordadas (NO implementadas aqui):
    - draft/pending/private -> publish: exige title y content no vacios;
      setea published_at solo la primera vez.
    - cualquiera -> trash: setea deleted_at.
    - trash -> otro: limpia deleted_at (restauracion).
    - Regla dura: post en trash no acepta update de campos -> 422 TRASH_POST_LOCKED.

    Consumidores (P6/Delete) codean contra esta interfaz desde el dia 1.
    """

    def can_transition(self, post, new_status: str) -> bool:
        raise NotImplementedError("PostStateService.can_transition — Spec 4 (P5)")

    def transition(self, post, new_status: str):
        raise NotImplementedError("PostStateService.transition — Spec 4 (P5)")
