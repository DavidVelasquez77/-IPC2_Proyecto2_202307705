# utils.py
class Nodo:
    def __init__(self, valor):
        self.valor = valor
        self.siguiente = None

class CustomList:
    def __init__(self):
        self.primero = None
        self.tamano = 0

    def add(self, item):
        nuevo_nodo = Nodo(item)
        if self.primero is None:
            self.primero = nuevo_nodo
        else:
            actual = self.primero
            while actual.siguiente:
                actual = actual.siguiente
            actual.siguiente = nuevo_nodo
        self.tamano += 1

    def get(self, index):
        actual = self.primero
        contador = 0
        while actual:
            if contador == index:
                return actual.valor
            actual = actual.siguiente
            contador += 1
        return None  # Si el índice está fuera de rango

    def update(self, index, new_value):
        actual = self.primero
        contador = 0
        while actual:
            if contador == index:
                actual.valor = new_value  # Actualiza el valor en el índice dado
                return True
            actual = actual.siguiente
            contador += 1
        return False  # Si el índice está fuera de rango

    def size(self):
        return self.tamano


    def __iter__(self):
        self.actual = None
        return self

    def __next__(self):
        if self.actual:
            valor = self.actual.valor
            self.actual = self.actual.siguiente
            return valor
        else:
            raise StopIteration

class Resultado:
    def __init__(self, tiempo, lineas):
        self.tiempo = tiempo  # Representa el tiempo (ej: "1er Segundo")
        self.lineas = lineas  # Es un CustomList con las acciones por línea de ensamblaje
