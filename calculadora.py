#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculadora en Python (solo libreria estandar).

Modos de uso
------------
  python calculadora.py                 # modo interactivo
  python calculadora.py "2 + 3 * 4"     # evalua la expresion y termina
  python calculadora.py -h              # ayuda de la linea de comandos

Como libreria
-------------
  >>> from calculadora import Calculadora, evaluar
  >>> evaluar("sqrt(16) + 2 ** 3")
  12.0
  >>> c = Calculadora()
  >>> c.evaluar("10 / 4")
  2.5
  >>> c.evaluar("ans * 2")      # 'ans' guarda el ultimo resultado
  5.0

Que soporta
-----------
  * Operadores: + - * / // % ** (tambien ^ como potencia) y parentesis.
  * Funciones: sqrt/raiz, abs, round/redondear, floor, ceil, factorial,
    sin, cos, tan, asin, acos, atan, log/ln, log10, log2, exp, min, max,
    radianes, grados.
  * Constantes: pi, e, tau.
  * Variables: ans (ultimo resultado) y m (memoria).

Seguridad: las expresiones se analizan con el modulo `ast` y solo se aceptan
los nodos listados en este archivo. Nunca se llama a eval(), por lo que una
expresion no puede ejecutar codigo arbitrario.
"""

from __future__ import annotations

import argparse
import ast
import math
import operator
import sys
from typing import Callable, Dict, List, Optional, Tuple, Union

__version__ = "1.0.0"

Numero = Union[int, float]


class ErrorCalculadora(Exception):
    """Error al evaluar una expresion: sintaxis, nombre desconocido, division por cero..."""


# ------------------------------------------------------------------ definiciones

_OPERADORES_BINARIOS: Dict[type, Callable[[Numero, Numero], Numero]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_OPERADORES_UNARIOS: Dict[type, Callable[[Numero], Numero]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

FUNCIONES: Dict[str, Callable[..., Numero]] = {
    "sqrt": math.sqrt, "raiz": math.sqrt,
    "abs": abs,
    "round": round, "redondear": round,
    "floor": math.floor, "ceil": math.ceil,
    "factorial": math.factorial,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp,
    "min": min, "max": max,
    "radianes": math.radians, "grados": math.degrees,
}

CONSTANTES: Dict[str, Numero] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

# Limites de seguridad: evitan expresiones que bloqueen el interprete o agoten
# la memoria (p. ej. 9 ** 9 ** 9 o factorial(10 ** 9)).
_MAX_DIGITOS = 4_000                                  # digitos de un resultado entero
_MAX_BITS = int(_MAX_DIGITOS * math.log2(10)) + 1     # equivalente en bits
_MAX_FACTORIAL = 1_000                                # argumento maximo de factorial()


# ------------------------------------------------------------------ comprobaciones

def _comprobar_resultado(valor: object) -> Numero:
    """Rechaza resultados que no sean numeros reales o enteros absurdamente grandes."""
    if isinstance(valor, complex):
        raise ErrorCalculadora("El resultado no es un numero real")
    if isinstance(valor, int) and valor.bit_length() > _MAX_BITS:
        raise ErrorCalculadora(f"Resultado demasiado grande (mas de {_MAX_DIGITOS} digitos)")
    return valor  # type: ignore[return-value]


def _comprobar_potencia(base: Numero, exponente: Numero) -> None:
    """Estima el tamano de base ** exponente ANTES de calcularlo."""
    if isinstance(base, int) and isinstance(exponente, int) and abs(base) > 1 and exponente > 0:
        if exponente * math.log10(abs(base)) > _MAX_DIGITOS:
            raise ErrorCalculadora(f"Resultado demasiado grande (mas de {_MAX_DIGITOS} digitos)")


def _comprobar_factorial(args: List[Numero]) -> None:
    if len(args) == 1 and isinstance(args[0], (int, float)) and args[0] > _MAX_FACTORIAL:
        raise ErrorCalculadora(f"factorial() admite como maximo {_MAX_FACTORIAL}")


def _es_entero_impar(n: Numero) -> bool:
    try:
        return n == int(n) and int(n) % 2 == 1
    except (OverflowError, ValueError):
        return False


# ------------------------------------------------------------------ evaluacion

def _operar_binario(tipo_op: type, izq: Numero, der: Numero) -> Numero:
    """Aplica un operador binario traduciendo los errores de Python a ErrorCalculadora."""
    if tipo_op is ast.Pow:
        _comprobar_potencia(izq, der)
    try:
        resultado = _OPERADORES_BINARIOS[tipo_op](izq, der)
    except ZeroDivisionError:
        raise ErrorCalculadora("Division por cero") from None
    except OverflowError:
        raise ErrorCalculadora("Resultado demasiado grande") from None
    return _comprobar_resultado(resultado)


def _llamar_funcion(nombre: str, args: List[Numero]) -> Numero:
    clave = nombre.lower()
    funcion = FUNCIONES.get(clave)
    if funcion is None:
        raise ErrorCalculadora(f"Funcion desconocida: '{nombre}'")
    if clave == "factorial":
        _comprobar_factorial(args)
    try:
        resultado = funcion(*args)
    except ZeroDivisionError:
        raise ErrorCalculadora("Division por cero") from None
    except OverflowError:
        raise ErrorCalculadora("Resultado demasiado grande") from None
    except ValueError:
        argumentos = ", ".join(formatear(a) for a in args)
        raise ErrorCalculadora(f"Error matematico: {clave}({argumentos}) no esta definido") from None
    except TypeError:
        raise ErrorCalculadora(f"Argumentos invalidos para {clave}()") from None
    return _comprobar_resultado(resultado)


class _Evaluador(ast.NodeVisitor):
    """Recorre el arbol sintactico y calcula su valor; rechaza todo nodo no previsto."""

    def __init__(self, variables: Dict[str, Numero]) -> None:
        self.variables = {k.lower(): v for k, v in variables.items()}

    def visit_Expression(self, nodo: ast.Expression) -> Numero:
        return self.visit(nodo.body)

    def visit_Constant(self, nodo: ast.Constant) -> Numero:
        valor = nodo.value
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ErrorCalculadora(f"Valor no permitido: {valor!r}")
        return _comprobar_resultado(valor)

    def visit_Name(self, nodo: ast.Name) -> Numero:
        nombre = nodo.id.lower()
        if nombre in self.variables:
            return self.variables[nombre]
        if nombre in CONSTANTES:
            return CONSTANTES[nombre]
        raise ErrorCalculadora(f"Nombre desconocido: '{nodo.id}'")

    def visit_UnaryOp(self, nodo: ast.UnaryOp) -> Numero:
        op = _OPERADORES_UNARIOS.get(type(nodo.op))
        if op is None:
            raise ErrorCalculadora("Operador no permitido")
        return op(self.visit(nodo.operand))

    def visit_BinOp(self, nodo: ast.BinOp) -> Numero:
        tipo = type(nodo.op)
        if tipo not in _OPERADORES_BINARIOS:
            raise ErrorCalculadora("Operador no permitido")
        return _operar_binario(tipo, self.visit(nodo.left), self.visit(nodo.right))

    def visit_Call(self, nodo: ast.Call) -> Numero:
        if not isinstance(nodo.func, ast.Name):
            raise ErrorCalculadora("Llamada no permitida")
        if nodo.keywords:
            raise ErrorCalculadora("No se admiten argumentos con nombre")
        return _llamar_funcion(nodo.func.id, [self.visit(a) for a in nodo.args])

    def generic_visit(self, nodo: ast.AST) -> Numero:
        raise ErrorCalculadora(f"Elemento no permitido en la expresion: {type(nodo).__name__}")


def _recortar(texto: str, maximo: int = 60) -> str:
    return texto if len(texto) <= maximo else texto[:maximo] + "..."


def evaluar(expresion: str, variables: Optional[Dict[str, Numero]] = None) -> Numero:
    """Evalua una expresion aritmetica de forma segura y devuelve su valor.

    >>> evaluar("2 + 3 * 4")
    14
    >>> evaluar("2 ^ 10")
    1024
    >>> evaluar("x * 2", {"x": 21})
    42
    """
    texto = expresion.strip().replace("^", "**")
    if not texto:
        raise ErrorCalculadora("Expresion vacia")
    try:
        arbol = ast.parse(texto, mode="eval")
    except (SyntaxError, ValueError):
        raise ErrorCalculadora(f"Expresion invalida: {_recortar(expresion.strip())!r}") from None
    except (RecursionError, MemoryError):
        raise ErrorCalculadora("Expresion demasiado compleja") from None
    try:
        return _Evaluador(variables or {}).visit(arbol)
    except RecursionError:
        raise ErrorCalculadora("Expresion demasiado compleja") from None


def formatear(valor: Numero, decimales: Optional[int] = None) -> str:
    """Devuelve el valor como texto legible: 4.0 -> '4', 0.1 + 0.2 -> '0.3'.

    >>> formatear(4.0)
    '4'
    >>> formatear(0.1 + 0.2)
    '0.3'
    >>> formatear(2 / 3, 4)
    '0.6667'
    """
    if decimales is not None:
        try:
            return f"{valor:.{decimales}f}"
        except OverflowError:       # entero demasiado grande para convertirlo a float
            return str(valor)
    if isinstance(valor, int):
        return str(valor)
    if math.isnan(valor) or math.isinf(valor):
        return str(valor)
    if valor.is_integer() and abs(valor) < 1e15:
        return str(int(valor))
    return f"{valor:.12g}"


# ------------------------------------------------------------------ calculadora

class Calculadora:
    """Calculadora con historial, memoria y la variable ``ans`` (ultimo resultado).

    >>> c = Calculadora()
    >>> c.sumar(2, 3)
    5
    >>> c.evaluar("ans * 10")
    50
    >>> c.memoria_sumar()          # M+ guarda el ultimo resultado en la memoria
    >>> c.evaluar("m / 5")
    10.0
    >>> len(c.historial)
    3
    """

    def __init__(self) -> None:
        self.ans: Numero = 0
        self.memoria: Numero = 0
        self.historial: List[Tuple[str, Numero]] = []

    # -- operaciones basicas ---------------------------------------------------

    def sumar(self, a: Numero, b: Numero) -> Numero:
        return self._registrar(f"{a} + {b}", _operar_binario(ast.Add, a, b))

    def restar(self, a: Numero, b: Numero) -> Numero:
        return self._registrar(f"{a} - {b}", _operar_binario(ast.Sub, a, b))

    def multiplicar(self, a: Numero, b: Numero) -> Numero:
        return self._registrar(f"{a} * {b}", _operar_binario(ast.Mult, a, b))

    def dividir(self, a: Numero, b: Numero) -> Numero:
        return self._registrar(f"{a} / {b}", _operar_binario(ast.Div, a, b))

    def potencia(self, base: Numero, exponente: Numero) -> Numero:
        return self._registrar(f"{base} ** {exponente}", _operar_binario(ast.Pow, base, exponente))

    def raiz(self, radicando: Numero, indice: Numero = 2) -> Numero:
        """Raiz n-esima (cuadrada por defecto). raiz(27, 3) -> 3.0"""
        if indice == 0:
            raise ErrorCalculadora("El indice de la raiz no puede ser 0")
        if radicando < 0:
            if not _es_entero_impar(indice):
                raise ErrorCalculadora("No existe raiz real de indice par de un numero negativo")
            resultado = -self._raiz_positiva(-radicando, indice)
        else:
            resultado = self._raiz_positiva(radicando, indice)
        return self._registrar(f"raiz({radicando}, {indice})", resultado)

    def porcentaje(self, valor: Numero, porcentaje: Numero) -> Numero:
        """Porcentaje de un valor. porcentaje(200, 15) -> 30.0"""
        resultado = _operar_binario(ast.Div, _operar_binario(ast.Mult, valor, porcentaje), 100)
        return self._registrar(f"{porcentaje}% de {valor}", resultado)

    @staticmethod
    def _raiz_positiva(x: Numero, n: Numero) -> Numero:
        if n == 2:
            return math.sqrt(x)
        resultado = _operar_binario(ast.Pow, x, 1 / n)
        if isinstance(n, int) and n > 0:
            aprox = round(resultado)
            if aprox ** n == x:     # corrige el error de coma flotante en raices exactas: 64 ** (1/3)
                return float(aprox)
        return resultado

    # -- expresiones -----------------------------------------------------------

    def evaluar(self, expresion: str) -> Numero:
        """Evalua una expresion; 'ans' es el ultimo resultado y 'm' la memoria."""
        resultado = evaluar(expresion, {"ans": self.ans, "m": self.memoria})
        return self._registrar(expresion.strip(), resultado)

    def _registrar(self, expresion: str, resultado: Numero) -> Numero:
        self.ans = resultado
        self.historial.append((expresion, resultado))
        return resultado

    def limpiar(self) -> None:
        """Borra el historial y reinicia 'ans' (la memoria se conserva)."""
        self.historial.clear()
        self.ans = 0

    # -- memoria (M+, M-, MR, MC) ----------------------------------------------

    def memoria_sumar(self, valor: Optional[Numero] = None) -> None:
        """M+: suma a la memoria el valor dado o, por defecto, el ultimo resultado."""
        self.memoria = _operar_binario(ast.Add, self.memoria, self.ans if valor is None else valor)

    def memoria_restar(self, valor: Optional[Numero] = None) -> None:
        """M-: resta de la memoria el valor dado o, por defecto, el ultimo resultado."""
        self.memoria = _operar_binario(ast.Sub, self.memoria, self.ans if valor is None else valor)

    def memoria_leer(self) -> Numero:
        """MR: devuelve el contenido de la memoria."""
        return self.memoria

    def memoria_borrar(self) -> None:
        """MC: pone la memoria a 0."""
        self.memoria = 0


# ------------------------------------------------------------------ modo interactivo

AYUDA = """\
Escriba una expresion y pulse Enter. Ejemplos:
  2 + 3 * 4          (2 + 3) * 4        2 ^ 10          10 % 3
  sqrt(2)            raiz(81)           sin(pi / 2)     log(100, 10)
  factorial(5)       round(2 / 3, 4)    ans * 2         m + 1

Operadores: + - * / // % ** ^ y parentesis.
Funciones : sqrt raiz abs round redondear floor ceil factorial sin cos tan
            asin acos atan log ln log10 log2 exp min max radianes grados
Constantes: pi e tau        Variables: ans (ultimo resultado), m (memoria)

Comandos:
  ayuda / ?     esta ayuda                 historial   operaciones realizadas
  m+ / m-       sumar / restar ans a m     mr / mc     leer / borrar la memoria
  limpiar       borrar el historial        salir       terminar (tambien Ctrl+D)"""


def modo_interactivo(calc: Optional[Calculadora] = None,
                     entrada: Optional[Callable[[str], str]] = None,
                     salida: Optional[Callable[[str], None]] = None) -> int:
    """Bucle leer-evaluar-imprimir.

    Por defecto lee con input() y escribe con print(); ambos se pueden sustituir
    (por ejemplo en los tests) pasando `entrada` y `salida`.
    """
    calc = calc if calc is not None else Calculadora()
    entrada = entrada if entrada is not None else input
    salida = salida if salida is not None else print
    salida(f"Calculadora {__version__}. Escriba 'ayuda' para ver los comandos o 'salir' para terminar.")
    while True:
        try:
            linea = entrada("> ").strip()
        except (EOFError, KeyboardInterrupt):
            salida("")
            return 0
        if not linea:
            continue
        comando = linea.lower()
        if comando in ("salir", "exit", "quit", "q"):
            return 0
        if comando in ("ayuda", "help", "?"):
            salida(AYUDA)
        elif comando in ("historial", "hist"):
            if not calc.historial:
                salida("(sin operaciones)")
            for i, (expresion, resultado) in enumerate(calc.historial, 1):
                salida(f"{i:3d}. {expresion} = {formatear(resultado)}")
        elif comando in ("limpiar", "clear"):
            calc.limpiar()
            salida("Historial borrado.")
        elif comando == "m+":
            calc.memoria_sumar()
            salida(f"M = {formatear(calc.memoria)}")
        elif comando == "m-":
            calc.memoria_restar()
            salida(f"M = {formatear(calc.memoria)}")
        elif comando == "mr":
            salida(f"M = {formatear(calc.memoria)}")
        elif comando == "mc":
            calc.memoria_borrar()
            salida("Memoria borrada.")
        else:
            try:
                salida(f"= {formatear(calc.evaluar(linea))}")
            except ErrorCalculadora as e:
                salida(f"Error: {e}")


# ------------------------------------------------------------------ linea de comandos

def _decimales(texto: str) -> int:
    n = int(texto)
    if n < 0:
        raise argparse.ArgumentTypeError("la precision no puede ser negativa")
    return n


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="calculadora",
        description="Calculadora de linea de comandos. Sin argumentos abre el modo interactivo.",
        epilog='Ejemplos: python calculadora.py "(2 + 3) * 4"      python calculadora.py -- "-5 + 3"\n'
               "Use comillas para que la shell no interprete * ni parentesis, y '--' si la "
               "expresion empieza por un signo menos.")
    ap.add_argument("expresion", nargs="*",
                    help="expresion a evaluar; si se omite, se abre el modo interactivo")
    ap.add_argument("-p", "--precision", type=_decimales, metavar="N",
                    help="mostrar el resultado con N decimales")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)

    if not a.expresion:
        return modo_interactivo()

    try:
        resultado = evaluar(" ".join(a.expresion))
    except ErrorCalculadora as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(formatear(resultado, a.precision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
