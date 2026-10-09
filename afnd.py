class AFND:
    def __init__(self):
        # Estados mapeados numéricamente:
        # 0: q0 (Espera / Inicio)
        # 1: qC (Candidatos Múltiples - No Determinismo)
        # 2: qR (Rechazo / Revisión Manual)
        # 3: qM (Aceptación - Match Confirmado)
        self.Q = {0, 1, 2, 3}
        self.Sigma = {'E', 'P', 'S', 'X'}
        self.q0 = 0
        self.F = {3}
        
        # Estado actual del autómata
        self.estado_actual = self.q0
        
        # Tabla de transiciones δ: (estado_actual, simbolo) -> conjunto de nuevos estados
        self.delta = {
            (0, 'E'): {3},
            (0, 'P'): {1},
            (0, 'X'): {2},
            (1, 'S'): {3},
            (1, 'X'): {2},
            (2, 'S'): {3}
        }

    def reiniciar(self):
        """Restablece el autómata al estado inicial q0."""
        self.estado_actual = self.q0
        return self.estado_actual

    def procesar_evento(self, simbolo):
        """
        Procesa un símbolo del alfabeto Σ = {E, P, S, X}.
        Retorna el nuevo estado numérico o None si la transición no es válida (conjunto vacío).
        """
        if simbolo not in self.Sigma:
            raise ValueError(f"Símbolo '{simbolo}' no pertenece al alfabeto {self.Sigma}")
        
        transicion = self.delta.get((self.estado_actual, simbolo), set())
        
        if transicion:
            # Dado que las salidas activas colapsan a un único estado destino:
            self.estado_actual = list(transicion)[0]
            return self.estado_actual
        else:
            # Representa la transición hacia ∅ (caso no permitido / sin cambio)
            return None

    def es_aceptado(self):
        """Verifica si el autómata se encuentra en el estado de aceptación qM (3)."""
        return self.estado_actual in self.F

    def obtener_estado(self):
        """Devuelve el estado numérico actual."""
        return self.estado_actual