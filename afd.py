class AFD:
    def __init__(self):
        self.Q = {0, 1, 2, 3}
        self.Sigma = {'v', 'a', 'e'}
        self.q0 = 0
        self.F = {2}
        self.qE = 3
        
        self.estado_actual = self.q0
        
        self.delta = {
            (0, 'v'): 1,  
            (1, 'a'): 2,  
            
            (0, 'a'): 3, (0, 'e'): 3,
            (1, 'v'): 3, (1, 'e'): 3,
            
            (2, 'v'): 3, (2, 'a'): 3, (2, 'e'): 3,
            
            (3, 'v'): 3, (3, 'a'): 3, (3, 'e'): 3
        }

    def reiniciar(self):
        self.estado_actual = self.q0
        return self.estado_actual

    def transicion(self, simbolo):
        if simbolo not in self.Sigma:
            raise ValueError(f"Símbolo '{simbolo}' no pertenece al alfabeto {self.Sigma}")
        
        self.estado_actual = self.delta.get((self.estado_actual, simbolo), self.qE)
        return self.estado_actual

    def es_aceptado(self):
        return self.estado_actual in self.F

    def es_trampa(self):
        return self.estado_actual == self.qE

    def obtener_estado(self):
        return self.estado_actual