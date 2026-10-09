class AFD:
    def __init__(self):
        # Estados mapeados numéricamente:
        # 0: q0 (Identidad Confirmada - Esperando pago)
        # 1: q1 (Pago Validado - Listo para ingreso)
        # 2: q2 (Aceptación - Asistencia Registrada y Ticket Entregado)
        # 3: qE (Estado Trampa / Rechazo / Doble Ingreso)
        self.Q = {0, 1, 2, 3}
        self.Sigma = {'v', 'a', 'e'}
        self.q0 = 0
        self.F = {2}
        self.qE = 3
        
        # Estado actual del autómata
        self.estado_actual = self.q0
        
        # Tabla de transiciones δ: (estado_actual, simbolo) -> nuevo_estado
        self.delta = {
            # Camino Feliz
            (0, 'v'): 1,  # Validar pago en Tesorería
            (1, 'a'): 2,  # Marcar Asistencia + Ticket simultáneamente
            
            # Transiciones explícitas al estado trampa (qE = 3)
            (0, 'a'): 3, (0, 'e'): 3,
            (1, 'v'): 3, (1, 'e'): 3,
            
            # Intento de reingreso (Si ya está en q2 y vuelve a marcar 'a' o 'v')
            (2, 'v'): 3, (2, 'a'): 3, (2, 'e'): 3,
            
            # Estado sumidero / trampa (qE = 3)
            (3, 'v'): 3, (3, 'a'): 3, (3, 'e'): 3
        }

    def reiniciar(self):
        """Restablece el autómata al estado inicial q0."""
        self.estado_actual = self.q0
        return self.estado_actual

    def transicion(self, simbolo):
        """
        Ejecuta la función de transición δ(estado_actual, simbolo).
        Transita hacia el nuevo estado (incluyendo el estado trampa 3 si aplica).
        """
        if simbolo not in self.Sigma:
            raise ValueError(f"Símbolo '{simbolo}' no pertenece al alfabeto {self.Sigma}")
        
        self.estado_actual = self.delta.get((self.estado_actual, simbolo), self.qE)
        return self.estado_actual

    def es_aceptado(self):
        """Verifica si el autómata se encuentra en el estado final q2 (2)."""
        return self.estado_actual in self.F

    def es_trampa(self):
        """Verifica si la transacción cayó en el estado trampa qE (3)."""
        return self.estado_actual == self.qE

    def obtener_estado(self):
        """Devuelve el estado numérico actual."""
        return self.estado_actual