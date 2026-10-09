class AFND:
    def __init__(self):
        self.Q = {0, 1, 2, 3}
        self.Sigma = {'E', 'P', 'S', 'X'}
        self.q0 = 0
        self.F = {3}
        
        self.estado_actual = self.q0
        
        self.delta = {
            (0, 'E'): {3},
            (0, 'P'): {1},
            (0, 'X'): {2},
            (1, 'S'): {3},
            (1, 'X'): {2},
            (2, 'S'): {3}
        }

    def reiniciar(self):
        self.estado_actual = self.q0
        return self.estado_actual

    def procesar_evento(self, simbolo):
        if simbolo not in self.Sigma:
            raise ValueError(f"Símbolo '{simbolo}' no pertenece al alfabeto {self.Sigma}")
        
        transicion = self.delta.get((self.estado_actual, simbolo), set())
        
        if transicion:
            self.estado_actual = list(transicion)[0]
            return self.estado_actual
        else:
            return None

    def es_aceptado(self):
        return self.estado_actual in self.F

    def obtener_estado(self):
        return self.estado_actual