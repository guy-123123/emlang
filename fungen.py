from decimal import Decimal
from fractions import Fraction
import os
import re
import subprocess
import sys
import interpreter

VALID = set("1ejcdhsr~")


# --- OPERATOR-OVERLOADED BYTECODE STRING ---
def _to_eml(val) -> "EmlExpr":
  """Converts raw Python numbers into EmlExpr via emit(), or passes EmlExpr through."""
  if isinstance(val, EmlExpr):
    return val
  if isinstance(val, (int, float, complex)):
    return emit(val)
  return EmlExpr(str(val))


class EmlExpr(str):
  """A string of .eml instructions supporting native Python math & comparison operators."""

  # Arithmetic
  def __add__(self, other):
    return EmlExpr(add(self, _to_eml(other)))

  def __radd__(self, other):
    return EmlExpr(add(_to_eml(other), self))

  def __sub__(self, other):
    return EmlExpr(sub(self, _to_eml(other)))

  def __rsub__(self, other):
    return EmlExpr(sub(_to_eml(other), self))

  def __mul__(self, other):
    return EmlExpr(mul(self, _to_eml(other)))

  def __rmul__(self, other):
    return EmlExpr(mul(_to_eml(other), self))

  def __truediv__(self, other):
    return EmlExpr(div(self, _to_eml(other)))

  def __rtruediv__(self, other):
    return EmlExpr(div(_to_eml(other), self))

  def __pow__(self, other):
    return EmlExpr(power(self, _to_eml(other)))

  def __rpow__(self, other):
    return EmlExpr(power(_to_eml(other), self))

  def __neg__(self):
    return EmlExpr(negate(self))

  def __pos__(self):
    return self

  # Comparisons
  def __lt__(self, other):
    return EmlExpr(lt(self, _to_eml(other)))

  def __le__(self, other):
    return EmlExpr(lte(self, _to_eml(other)))

  def __gt__(self, other):
    return EmlExpr(gt(self, _to_eml(other)))

  def __ge__(self, other):
    return EmlExpr(gte(self, _to_eml(other)))

  def __eq__(self, other):
    return EmlExpr(eq(self, _to_eml(other)))

  def __ne__(self, other):
    return EmlExpr(neq(self, _to_eml(other)))

  # Boolean / Bitwise
  def __and__(self, other):
    return EmlExpr(AND(self, _to_eml(other)))

  def __rand__(self, other):
    return EmlExpr(AND(_to_eml(other), self))

  def __or__(self, other):
    return EmlExpr(OR(self, _to_eml(other)))

  def __ror__(self, other):
    return EmlExpr(OR(_to_eml(other), self))

  def __xor__(self, other):
    return EmlExpr(XOR(self, _to_eml(other)))

  def __rxor__(self, other):
    return EmlExpr(XOR(_to_eml(other), self))

  def __invert__(self):
    return EmlExpr(NOT(self))


# --- CORE PRIMITIVES & STACK MANIPULATION ---
def eml(x, y) -> EmlExpr:
  x_s = "1" if (type(x) is int and x == 1) else _to_eml(x)
  y_s = "1" if (type(y) is int and y == 1) else _to_eml(y)
  return EmlExpr(f"{x_s}{y_s}e")


def conj(x) -> EmlExpr:
  x_s = "1" if (type(x) is int and x == 1) else _to_eml(x)
  return EmlExpr(f"{x_s}~")


def dh(x="") -> EmlExpr:
  if x == "":
    return EmlExpr("dh")
  x_s = "1" if (type(x) is int and x == 1) else _to_eml(x)
  return EmlExpr(f"{x_s}dh")


def h() -> EmlExpr:
  return EmlExpr("h")


def select_dir(x) -> EmlExpr:  # 0: main -> stack2, 1: stack2 -> main
  return EmlExpr(f"{mul(_to_eml(x), i())}r")


def swap(x="") -> EmlExpr:
  if x == "":
    return EmlExpr("s")
  return EmlExpr(f"{_to_eml(x)}s")


# --- MATH OPS ---
def exp(x) -> EmlExpr:
  return eml(x, 1)


def ln(x) -> EmlExpr:
  return conj(eml(1, exp(eml(1, conj(x)))))


def sub(x, y) -> EmlExpr:
  return eml(ln(x), exp(y))


def zero() -> EmlExpr:
  return ln(1)


def negate(x) -> EmlExpr:
  return sub(zero(), x)


def add(x, y) -> EmlExpr:
  return sub(x, negate(y))


def mul(x, y) -> EmlExpr:
  return exp(add(ln(x), ln(y)))


def div(x, y) -> EmlExpr:
  return exp(sub(ln(x), ln(y)))


def power(x, y) -> EmlExpr:
  return exp(mul(y, ln(x)))


def root(x, base) -> EmlExpr:
  return power(x, div(1, base))


def sqrt(x) -> EmlExpr:
  return root(x, add(1, 1))


def sqpw(x) -> EmlExpr:
  return power(x, add(1, 1))


def real(z) -> EmlExpr:
  return div(add(dh(z), conj(h())), add(1, 1))


def imag(z) -> EmlExpr:
  two_i = mul(add(1, 1), i())
  return div(sub(dh(z), conj(h())), two_i)


# --- BOOLEAN & COMPARISONS ---
def NOT(x) -> EmlExpr:
  return sub(1, x)


def AND(x, y) -> EmlExpr:
  return mul(x, y)


def NAND(x, y) -> EmlExpr:
  return NOT(AND(x, y))


def OR(x, y) -> EmlExpr:
  return NAND(NOT(x), NOT(y))


def XOR(x, y) -> EmlExpr:
  diff = dh(sub(x, y))
  return mul(diff, h())


def is_zero(x) -> EmlExpr:
  x_sq = sqpw(x)
  return power(zero(), x_sq)


def is_zero_ala(x) -> EmlExpr:
  return NOT(is_zero(x))


def eq(a, b) -> EmlExpr:
  return is_zero(sub(a, b))


def neq(a, b) -> EmlExpr:
  return is_zero_ala(sub(a, b))


def lt(a, b) -> EmlExpr:
  """Returns 1 if a < b (for real numbers), else 0."""
  # d = a - b; duplicate d onto hold_reg and stack2 cleanly:
  # Using pure algebra: (1 - d / (sqrt(d^2) + is_zero(d))) / 2 * is_zero_ala(d)
  to_s2 = f"{mul(zero(), i())}r"
  from_s2 = f"{mul(1, i())}r"
  # Push d onto stack2:
  push_d = f"{sub(a, b)}{to_s2}s"
  # Helper expressions that peek vs pop stack2:
  peek_d = f"{from_s2}sd{to_s2}s"
  pop_d = f"{from_s2}s"

  two = add(1, 1)
  # sign_term = (1 - peek_d / (sqrt(sqpw(peek_d)) + is_zero(peek_d))) / 2
  abs_plus_z = add(sqrt(sqpw(peek_d)), is_zero(peek_d))
  sign_bit = div(sub(1, div(peek_d, abs_plus_z)), two)
  return EmlExpr(f"{push_d}{AND(sign_bit, is_zero_ala(pop_d))}")




def gt(a, b) -> EmlExpr:
  return lt(b, a)


def lte(a, b) -> EmlExpr:
  return NOT(gt(a, b))


def gte(a, b) -> EmlExpr:
  return NOT(lt(a, b))


# --- CONSTANTS ---
def i() -> EmlExpr:
  return sqrt(negate(1))


def e() -> EmlExpr:
  return eml(1, 1)


def pi() -> EmlExpr:
  return mul(negate(i()), ln(negate(1)))


# --- TRIGONOMETRY & INVERSE TRIG ---
def cos(x) -> EmlExpr:
  e_ix = power(e(), mul(i(), x))
  return div(add(dh(e_ix), div(1, h())), add(1, 1))


def sin(x) -> EmlExpr:
  half_pi = div(pi(), add(1, 1))
  return cos(sub(x, half_pi))


def tan(x) -> EmlExpr:
  return div(sin(dh(x)), cos(h()))


def sec(x) -> EmlExpr:
  return div(1, cos(x))


def csc(x) -> EmlExpr:
  return div(1, sin(x))


def cot(x) -> EmlExpr:
  return div(cos(dh(x)), sin(h()))


def arcsin(x) -> EmlExpr:
  return mul(negate(i()), ln(add(mul(i(), dh(x)), sqrt(sub(1, sqpw(h()))))))


def arccos(x) -> EmlExpr:
  return add(negate(arcsin(x)), div(pi(), add(1, 1)))


def arctan(x) -> EmlExpr:
  two = add(1, 1)
  ix = dh(mul(i(), x))
  return mul(div(i(), two), ln(div(sub(1, ix), add(1, h()))))


def arcsec(x) -> EmlExpr:
  return arccos(div(1, x))


def arccsc(x) -> EmlExpr:
  return arcsin(div(1, x))


def arccot(x) -> EmlExpr:
  return sub(div(pi(), add(1, 1)), arctan(x))


# --- LITERAL EMISSION ---
def _emit_digit(d: int) -> EmlExpr:
  if d == 0:
    return zero()
  res = EmlExpr("1")
  for _ in range(d - 1):
    res = add(res, "1")
  return res


def emit_int(n: int) -> EmlExpr:
  if n == 0:
    return zero()
  if n < 0:
    return negate(emit_int(-n))

  digits = [int(ch) for ch in str(n)]
  ten = _emit_digit(10)

  acc = _emit_digit(digits[0])
  for d in digits[1:]:
    acc = mul(acc, ten)
    if d != 0:
      acc = add(acc, _emit_digit(d))
  return EmlExpr(acc)


def emit_float(val) -> EmlExpr:
  frac = Fraction(Decimal(str(val)))
  if frac.denominator == 1:
    return emit_int(frac.numerator)
  return div(emit_int(frac.numerator), emit_int(frac.denominator))


def emit(x) -> EmlExpr:
  if x.imag == 0:
    return emit_float(x.real)
  if x.real == 0:
    return mul(i(), emit_float(x.imag))
  return add(emit_float(x.real), mul(i(), emit_float(x.imag)))


# --- I/O & CONTROL FLOW ---
def out_num(val) -> EmlExpr:
  two_i = mul(add(1, 1), i())
  return EmlExpr(f"{_to_eml(val)}{two_i}c")


def in_num() -> EmlExpr:
  return EmlExpr(f"{i()}c")

def out_char(val) -> EmlExpr:
  """Prints a single ASCII character from a runtime value (sys_code 3)."""
  three_i = mul(_emit_digit(3), i())
  return EmlExpr(f"{_to_eml(val)}{three_i}c")


def out_str(text: str) -> EmlExpr:
  """Prints a Python string using delta-encoding with hold_reg (no empty-string ops)."""
  if not text:
    return EmlExpr("")

  three_i = mul(_emit_digit(3), i())
  chunks = []

  # 1. Push first character's ASCII code onto stack
  prev = ord(text[0])  # <-- remember square brackets around 0!
  chunks.append(str(emit_int(prev)))

  # 2. For each next character: duplicate top of stack -> hold_reg, print stack copy,
  #    and shift the hold_reg copy by delta = curr - prev
  for ch in text[1:]:
    curr = ord(ch)
    delta = curr - prev
    chunks.append(f"dh{three_i}c")  # Duplicate to hold_reg, print top of stack
    if delta > 0:
      chunks.append(str(add(h(), emit_int(delta))))
    elif delta < 0:
      chunks.append(str(sub(h(), emit_int(-delta))))
    else:
      chunks.append("h")  # Unchanged char: just pop hold_reg back onto stack
    prev = curr

  # 3. Print the final character
  chunks.append(f"{three_i}c")
  return EmlExpr("".join(chunks))
def in_line_s2() -> EmlExpr:
  """Prompts user for a full line and pushes all ASCII codes onto stack2 (0-terminated)."""
  five_i = mul(_emit_digit(5), i())
  return EmlExpr(f"{five_i}c")


def pop_s2() -> EmlExpr:
  """Pops one value from stack2 onto the main stack."""
  from_s2 = f"{mul(1, i())}r"
  return EmlExpr(f"{from_s2}s")


def push_s2(val="") -> EmlExpr:
  """Pushes a value from the main stack onto stack2."""
  to_s2 = f"{mul(zero(), i())}r"
  prefix = str(_to_eml(val)) if val != "" else ""
  return EmlExpr(f"{prefix}{to_s2}s")




def addr(cond, PC) -> EmlExpr:
  target = emit_int(PC) if isinstance(PC, int) else _to_eml(PC)
  return add(mul(i(), target), cond)


def _jmp_pure(ctrl) -> EmlExpr:
  return EmlExpr(f"{ctrl}j")


def jmp_if_1(cond, PC) -> EmlExpr:
  return _jmp_pure(addr(cond, PC))


def jnz(cond, PC) -> EmlExpr:
  return _jmp_pure(addr(is_zero_ala(cond), PC))


def jmp(PC) -> EmlExpr:
  return _jmp_pure(addr(1, PC))


def jz(cond, PC) -> EmlExpr:
  return _jmp_pure(addr(is_zero(cond), PC))


def instr_count(expr) -> int:
  code = emit(expr) if isinstance(expr, (int, float, complex)) else str(expr)
  return sum(1 for ch in code if ch in VALID)


# --- TWO-PASS ASSEMBLER ---
def assemble(source: str) -> str:
  lines = []
  for raw_line in source.splitlines():
    line = raw_line.split("#", 1)[0].strip()
    if line:
      lines.append(line)

  labels: dict[str, int] = {}
  seen_states = []

  while True:
    new_labels: dict[str, int] = {}
    pc = 0
    compiled_chunks = []

    for line in lines:
      if line.startswith("@"):
        name = line.rstrip(":").strip()
        new_labels[name] = pc
        continue

      resolved_line = re.sub(
          r"@[A-Za-z_]\w*",
          lambda m: str(labels.get(m.group(0), 0)),
          line,
      )

      chunk = str(
          eval(resolved_line, {"__builtins__": None}, allowed_functions)
      )
      compiled_chunks.append(chunk)
      pc += sum(1 for ch in chunk if ch in VALID)

    if new_labels == labels:
      return "".join(compiled_chunks)

    if new_labels in seen_states:
      target_labels = {
          k: max(s[k] for s in seen_states[-2:]) for k in new_labels
      }
      pc = 0
      final_chunks = []
      for line in lines:
        if line.startswith("@"):
          name = line.rstrip(":").strip()
          diff = target_labels[name] - pc
          if diff > 0:
            final_chunks.append("~~" * (diff // 2))
            pc += 2 * (diff // 2)
          continue
        resolved_line = re.sub(
            r"@[A-Za-z_]\w*",
            lambda m: str(target_labels.get(m.group(0), 0)),
            line,
        )
        chunk = str(
            eval(resolved_line, {"__builtins__": None}, allowed_functions)
        )
        final_chunks.append(chunk)
        pc += sum(1 for ch in chunk if ch in VALID)
      return "".join(final_chunks)

    seen_states.append(new_labels)
    labels = new_labels


# --- EXECUTION ENTRYPOINT ---
_EXCLUDED = {
    "interpreter",
    "os",
    "sys",
    "subprocess",
    "re",
    "Decimal",
    "Fraction",
    "EmlExpr",
    "assemble",
}





# Optional helper to push 2i and trigger sys_code 2 (numeric output)

allowed_functions = {k: v for k, v in globals().items()
                     if callable(v) and not k.startswith('_')
                     and k not in _EXCLUDED}

if __name__ == "__main__":
    mode = input("(1) expression (2) assembly file: ").strip()
    if mode == "2":
        fname = input("assembly file: ")
        with open(fname, encoding="utf-8") as f:
            code = assemble(f.read())
    else:
        code = eval(input("expression: "), {"__builtins__": None}, allowed_functions)
    with open("program.eml", "w", encoding="utf-8") as f:
        f.write(code)
    interpreter.run_program("program.eml", int(input("debug? (1/0): ")))
    input("Press Enter to close...")
