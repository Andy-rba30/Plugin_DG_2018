# -*- coding: utf-8 -*-
"""
Tests de la calculadora (calculadora.py, en la raiz del repositorio).

Cubren el evaluador de expresiones, los limites de seguridad, el formato de
resultados, la clase Calculadora (historial, ans, memoria), el modo interactivo
y la interfaz de linea de comandos.
"""

import doctest
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calculadora  # noqa: E402
from calculadora import (  # noqa: E402
    Calculadora, ErrorCalculadora, evaluar, formatear, main, modo_interactivo,
)


# ------------------------------------------------------------------ evaluar()

class TestEvaluar:

    @pytest.mark.parametrize("expresion, esperado", [
        ("2 + 3", 5),
        ("10 - 4", 6),
        ("6 * 7", 42),
        ("10 / 4", 2.5),
        ("10 // 4", 2),
        ("10 % 3", 1),
        ("2 ** 10", 1024),
        ("2 ^ 10", 1024),           # ^ se acepta como potencia
        ("2 + 3 * 4", 14),          # precedencia
        ("(2 + 3) * 4", 20),        # parentesis
        ("-5 + 3", -2),             # menos unario
        ("--5", 5),
        ("+5", 5),
        ("-2 ** 2", -4),            # -(2**2), como en matematicas y en Python
        ("2 ** 3 ** 2", 512),       # asociatividad por la derecha
        ("1.5 * 2", 3.0),
        ("1e3 + 1", 1001.0),
        ("7 % 3 + 7 // 3", 3),
    ])
    def test_aritmetica(self, expresion, esperado):
        assert evaluar(expresion) == esperado

    @pytest.mark.parametrize("expresion, esperado", [
        ("sqrt(16)", 4.0),
        ("raiz(81)", 9.0),
        ("abs(-3.5)", 3.5),
        ("round(2.567, 2)", 2.57),
        ("redondear(2.5)", 2),
        ("floor(2.7)", 2),
        ("ceil(2.1)", 3),
        ("factorial(5)", 120),
        ("log10(1000)", 3.0),
        ("log2(8)", 3.0),
        ("exp(0)", 1.0),
        ("min(3, 1, 2)", 1),
        ("max(3, 1, 2)", 3),
        ("grados(pi)", 180.0),
    ])
    def test_funciones(self, expresion, esperado):
        assert evaluar(expresion) == esperado

    def test_funciones_trigonometricas(self):
        assert evaluar("sin(pi / 2)") == pytest.approx(1.0)
        assert evaluar("cos(0)") == 1.0
        assert evaluar("tan(pi / 4)") == pytest.approx(1.0)
        assert evaluar("asin(1)") == pytest.approx(math.pi / 2)
        assert evaluar("acos(1)") == 0.0
        assert evaluar("atan(1) * 4") == pytest.approx(math.pi)
        assert evaluar("sin(radianes(90))") == pytest.approx(1.0)

    def test_logaritmos(self):
        assert evaluar("log(100, 10)") == pytest.approx(2.0)
        assert evaluar("ln(e)") == pytest.approx(1.0)
        assert evaluar("log(e ** 3)") == pytest.approx(3.0)

    def test_constantes(self):
        assert evaluar("pi") == math.pi
        assert evaluar("e") == math.e
        assert evaluar("tau") == 2 * math.pi

    def test_nombres_no_distinguen_mayusculas(self):
        assert evaluar("SQRT(4) + PI") == 2 + math.pi
        assert evaluar("Factorial(3)") == 6

    def test_variables(self):
        assert evaluar("x * 2 + y", {"x": 20, "y": 2}) == 42
        assert evaluar("X", {"x": 1}) == 1

    def test_espacios_y_expresion_vacia(self):
        assert evaluar("  1+1  ") == 2
        with pytest.raises(ErrorCalculadora, match="vacia"):
            evaluar("   ")

    def test_enteros_grandes_pero_razonables(self):
        assert evaluar("2 ** 100") == 2 ** 100
        assert evaluar("factorial(20)") == math.factorial(20)


# ------------------------------------------------------------------ errores y seguridad

class TestErrores:

    @pytest.mark.parametrize("expresion, mensaje", [
        ("1 / 0", "Division por cero"),
        ("1 % 0", "Division por cero"),
        ("1 // 0", "Division por cero"),
        ("0 ** -1", "Division por cero"),
        ("sqrt(-1)", "Error matematico"),
        ("log(0)", "Error matematico"),
        ("factorial(-1)", "Error matematico"),
        ("2 +", "Expresion invalida"),
        ("(2 + 3", "Expresion invalida"),
        ("2 3", "Expresion invalida"),
        ("foo(1)", "Funcion desconocida"),
        ("x + 1", "Nombre desconocido"),
        ("sqrt()", "Argumentos invalidos"),
        ("round(1.5, 1.5)", "Argumentos invalidos"),
        ("sqrt(x=4)", "argumentos con nombre"),
        ("(-8) ** (1/3)", "no es un numero real"),
        ("2 ** 100000", "demasiado grande"),
        ("9 ** 9 ** 9", "demasiado grande"),
        ("(10 ** 1000) ** 1000", "demasiado grande"),
        ("2.0 ** 10000", "demasiado grande"),
        ("exp(1000)", "demasiado grande"),
        ("factorial(100000)", "maximo"),
    ])
    def test_mensajes(self, expresion, mensaje):
        with pytest.raises(ErrorCalculadora, match=mensaje):
            evaluar(expresion)

    @pytest.mark.parametrize("expresion", [
        "__import__('os').system('echo hola')",
        "().__class__.__bases__[0].__subclasses__()",
        "open('/etc/passwd')",
        "'abc' * 3",
        "[1, 2, 3]",
        "1 if 1 else 2",
        "lambda: 1",
        "1 < 2",
        "1 & 2",
        "1 << 2",
        "~1",
        "not 1",
        "2j + 1",
        "True + 1",
        "None",
        "max(*[1, 2])",
        "math.pi",
        "(1)(2)",
    ])
    def test_rechaza_codigo_arbitrario(self, expresion):
        with pytest.raises(ErrorCalculadora):
            evaluar(expresion)

    def test_expresiones_patologicas_terminan_con_error_controlado(self):
        with pytest.raises(ErrorCalculadora):
            evaluar("-" * 1000 + "1")
        with pytest.raises(ErrorCalculadora):
            evaluar("(" * 500 + "1" + ")" * 500)
        with pytest.raises(ErrorCalculadora):
            evaluar("1" * 5000)

    def test_mensaje_de_expresion_invalida_se_recorta(self):
        with pytest.raises(ErrorCalculadora) as e:
            evaluar("(" * 500)
        assert len(str(e.value)) < 120


# ------------------------------------------------------------------ formatear()

class TestFormatear:

    @pytest.mark.parametrize("valor, esperado", [
        (5, "5"),
        (-7, "-7"),
        (4.0, "4"),
        (-4.0, "-4"),
        (2.5, "2.5"),
        (0.1 + 0.2, "0.3"),             # oculta el ruido de coma flotante
        (1 / 3, "0.333333333333"),
        (1e20, "1e+20"),
        (2 ** 100, str(2 ** 100)),
        (float("inf"), "inf"),
        (float("nan"), "nan"),
    ])
    def test_sin_precision(self, valor, esperado):
        assert formatear(valor) == esperado

    def test_con_precision(self):
        assert formatear(2 / 3, 4) == "0.6667"
        assert formatear(5, 2) == "5.00"
        assert formatear(1.0, 0) == "1"
        assert formatear(10 ** 400, 2) == str(10 ** 400)   # no cabe en float


# ------------------------------------------------------------------ Calculadora

class TestCalculadora:

    def test_operaciones_basicas(self):
        c = Calculadora()
        assert c.sumar(2, 3) == 5
        assert c.restar(10, 4) == 6
        assert c.multiplicar(6, 7) == 42
        assert c.dividir(10, 4) == 2.5
        assert c.potencia(2, 10) == 1024
        assert c.raiz(16) == 4.0
        assert c.raiz(27, 3) == 3.0
        assert c.raiz(64, 3) == 4.0          # 64 ** (1/3) da 3.9999999999999996 en coma flotante
        assert c.raiz(-27, 3) == -3.0
        assert c.raiz(0, 5) == 0.0
        assert c.raiz(2) == pytest.approx(math.sqrt(2))
        assert c.porcentaje(200, 15) == 30.0

    def test_errores_operaciones_basicas(self):
        c = Calculadora()
        with pytest.raises(ErrorCalculadora, match="Division por cero"):
            c.dividir(1, 0)
        with pytest.raises(ErrorCalculadora, match="indice"):
            c.raiz(4, 0)
        with pytest.raises(ErrorCalculadora, match="par"):
            c.raiz(-4, 2)
        with pytest.raises(ErrorCalculadora, match="demasiado grande"):
            c.potencia(10, 10 ** 6)
        assert c.historial == []             # las operaciones fallidas no se registran

    def test_ans_e_historial(self):
        c = Calculadora()
        assert c.ans == 0
        assert c.evaluar("ans + 5") == 5
        assert c.evaluar("ans * 3") == 15
        assert c.ans == 15
        assert c.historial == [("ans + 5", 5), ("ans * 3", 15)]
        c.sumar(1, 1)
        assert c.historial[-1] == ("1 + 1", 2)
        assert c.ans == 2
        c.limpiar()
        assert c.historial == []
        assert c.ans == 0

    def test_error_no_altera_el_estado(self):
        c = Calculadora()
        c.evaluar("7")
        with pytest.raises(ErrorCalculadora):
            c.evaluar("1 / 0")
        assert c.ans == 7
        assert len(c.historial) == 1

    def test_memoria(self):
        c = Calculadora()
        c.evaluar("12")
        c.memoria_sumar()                    # M = 12 (ultimo resultado)
        c.memoria_sumar(3)                   # M = 15
        c.memoria_restar(5)                  # M = 10
        assert c.memoria_leer() == 10
        assert c.evaluar("m * 2") == 20
        c.memoria_restar()                   # M = 10 - 20 = -10
        assert c.memoria == -10
        c.limpiar()
        assert c.memoria == -10              # limpiar() conserva la memoria
        c.memoria_borrar()
        assert c.memoria == 0


# ------------------------------------------------------------------ modo interactivo

def ejecutar_interactivo(lineas):
    """Ejecuta el bucle interactivo con entradas simuladas; devuelve (codigo, salidas)."""
    entradas = iter(lineas)
    salidas = []

    def entrada(_prompt):
        try:
            return next(entradas)
        except StopIteration:
            raise EOFError

    codigo = modo_interactivo(entrada=entrada, salida=salidas.append)
    return codigo, salidas


class TestModoInteractivo:

    def test_evalua_y_sale(self):
        codigo, salidas = ejecutar_interactivo(["2 + 2", "ans * 10", "salir"])
        assert codigo == 0
        assert "= 4" in salidas
        assert "= 40" in salidas

    def test_errores_no_interrumpen_el_bucle(self):
        codigo, salidas = ejecutar_interactivo(["1 / 0", "foo", "", "   ", "3 * 3", "q"])
        assert codigo == 0
        assert any(s.startswith("Error: Division por cero") for s in salidas)
        assert any(s.startswith("Error: Nombre desconocido") for s in salidas)
        assert "= 9" in salidas

    def test_comandos(self):
        codigo, salidas = ejecutar_interactivo([
            "5", "M+", "m+", "mr", "m-", "mc", "historial", "limpiar", "historial", "ayuda", "exit",
        ])
        assert codigo == 0
        assert salidas.count("M = 5") == 2       # tras el primer m+ y tras m-
        assert salidas.count("M = 10") == 2      # tras el segundo m+ y en mr
        assert "Memoria borrada." in salidas
        assert any("1. 5 = 5" in s for s in salidas)
        assert "Historial borrado." in salidas
        assert "(sin operaciones)" in salidas
        assert any("Comandos" in s for s in salidas)

    def test_fin_de_entrada_termina_limpiamente(self):
        codigo, salidas = ejecutar_interactivo(["1 + 1"])       # EOF tras la primera linea
        assert codigo == 0
        assert "= 2" in salidas

    def test_usa_la_calculadora_recibida(self):
        c = Calculadora()
        c.memoria_sumar(99)
        entradas = iter(["m", "salir"])
        salidas = []
        modo_interactivo(c, entrada=lambda _: next(entradas), salida=salidas.append)
        assert "= 99" in salidas
        assert c.historial == [("m", 99)]


# ------------------------------------------------------------------ linea de comandos

class TestCli:

    def test_expresion_en_varios_argumentos(self, capsys):
        assert main(["2", "+", "3", "*", "4"]) == 0
        assert capsys.readouterr().out.strip() == "14"

    def test_expresion_con_precision(self, capsys):
        assert main(["sqrt(2) ^ 2", "-p", "3"]) == 0
        assert capsys.readouterr().out.strip() == "2.000"

    def test_numero_negativo_inicial(self, capsys):
        assert main(["-5", "+", "3"]) == 0
        assert capsys.readouterr().out.strip() == "-2"
        assert main(["--", "-5 + 3"]) == 0
        assert capsys.readouterr().out.strip() == "-2"

    def test_error_devuelve_1(self, capsys):
        assert main(["1 / 0"]) == 1
        capturado = capsys.readouterr()
        assert capturado.out == ""
        assert "Division por cero" in capturado.err

    def test_precision_negativa_es_error_de_argumentos(self, capsys):
        with pytest.raises(SystemExit) as e:
            main(["1", "-p", "-1"])
        assert e.value.code == 2

    def test_sin_argumentos_abre_modo_interactivo(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "salir")
        assert main([]) == 0
        assert "Calculadora" in capsys.readouterr().out


# ------------------------------------------------------------------ doctests

def test_doctests_del_modulo():
    resultado = doctest.testmod(calculadora)
    assert resultado.attempted > 0
    assert resultado.failed == 0
