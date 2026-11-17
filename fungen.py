import subprocess
import sys
import os
import interpreter

def eml(x, y):
    return f"{x}{y}e"
def exp(x):
    return eml(x, 1)
def ln(x):
    return eml(1, exp(eml(1, x)))
def sub(x, y):
    return eml(ln(x), exp(y))
def zero():
    return ln(1)
def negate(x):
    return sub(zero(), x)
def add(x, y):
    return sub(x, negate(y))
def mul(x, y):
    return exp(add(ln(x), ln(y)))
def div(x, y):
    return exp(sub(ln(x), ln(y)))
def power(x, y):
    return exp(mul(y, ln(x)))
def root(x, base):
    return power(x, div(1, base))
def sqrt(x):
    return root(x,add(1,1))
def i():
    return negate(sqrt(negate(1)))
def e():
    return eml(1, 1)
def pi():
    return negate(mul(negate(i()), ln(negate(1))))

# Optional helper to push 2i and trigger sys_code 2 (numeric output)
def out_num(val):
    two_i = mul(add(1, 1), i())
    return f"{val}{two_i}c"

def in_num():
    return f"{i()}c"

allowed_functions = {
    "eml": eml,
    "exp": exp,
    "ln": ln,
    "sub": sub,
    "zero": zero,
    "negate": negate,
    "add": add,
    "mul": mul,
    "div": div,
    "power": power,
    "root": root,
    "i": i,
    "e": e,
    "pi": pi,
    "in_num": in_num,
}

print("Available functions: eml, exp, ln, sub, zero, negate, add, mul, div, power, root, i, e, pi, in_num")
user_expr = input("Enter function expression (e.g., pi() or add(in_num(), 1)): ")
debug_mode = int(input("Enable debug mode? (1/0): "))

raw_code = eval(user_expr, {"__builtins__": None}, allowed_functions)
code = out_num(raw_code)

base_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(base_dir, "program.eml")

with open(output_file, "w", encoding="utf-8") as f:
    f.write(code)

# Runs inside the exact same window!
interpreter.run_program(output_file, debug_mode)

# Pauses the window so you can read the output
input("Press Enter to close...")
