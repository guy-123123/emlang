import sys
from mpmath import mp

mp.dps = 100

def load_program(filename: str) -> list[str]:
    valid_instructions = {"1", "e", "j", "c", "d", "r", "l"}
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
    return [char for char in content if char in valid_instructions]

def clean_mpc(z, tol=mp.mpf('1e-50')) -> mp.mpc:
    """Snaps near-zero real/imag noise to exact 0 so branch cuts don't flip."""
    z = mp.mpc(z)
    re = mp.mpf('0') if abs(z.real) < tol else z.real
    im = mp.mpf('0') if abs(z.imag) < tol else z.imag
    return mp.mpc(re, im)

def eml(x: mp.mpc, y: mp.mpc) -> mp.mpc:
    return clean_mpc(mp.exp(y) - mp.log(x))

def format_stack(stk: list[mp.mpc]) -> str:
    """Formats mpmath complex numbers cleanly for debug and trace logs."""
    return "[" + ", ".join(mp.nstr(item, 15) for item in stk) + "]"

# --- WRAPPED IN A FUNCTION SO IT CAN BE CALLED DIRECTLY ---
def run_program(filename: str, debug: int = 0):
    program = load_program(filename)
    stack: list[mp.mpc] = []
    PC = 0

    def execitr(instruction: str):
        nonlocal PC
        if instruction == "1":  # push high-precision 1
            stack.append(mp.mpc(1, 0))
        elif instruction == "e":  # do eml (note: stack[-1] is x, stack[-2] is y)
            stack[-1] = eml(stack[-1], stack[-2])
            stack.pop(-2)
        elif instruction == "j":  # jump if 1
            savestack = stack.pop()
            if int(mp.nint(savestack.real)) == 1:
                PC = int(mp.nint(savestack.imag)) - 1
        elif instruction == "d":
            stack.append(stack[-1])
        elif instruction == "r":  # rotate right (top element moves to bottom)
            if len(stack) > 1:
                stack[:] = stack[-1:] + stack[:-1]
        elif instruction == "l":  # rotate left (bottom element moves to top)
            if len(stack) > 1:
                stack[:] = stack[1:] + stack[:1]
        elif instruction == "c":  # call sys instructions
            sys_code = int(mp.nint(stack[-1].imag))
            if sys_code == 1:  # numeric input
                stack.pop()
                val = complex(input("input num pls: "))
                stack.append(mp.mpc(val.real, val.imag))
                stacktrace.write(f'inputed: {mp.nstr(stack[-1], 15)}\n')
            elif sys_code == 2:  # numeric output
                stack.pop()
                out_val = clean_mpc(stack.pop())
                print(mp.nstr(out_val.real, 15))
                stacktrace.write(f'outputed: {mp.nstr(out_val, 15)}\n')
            elif sys_code == 3:  # ASCII output
                stack.pop()
                out_val = stack.pop()
                print(chr(int(mp.nint(out_val.real))), end="")
                stacktrace.write(f'outputed: {mp.nstr(out_val, 15)}\n')
            elif sys_code == 4:  # ASCII input
                stack.pop()
                char = input("input letter pls: ")[0]
                stack.append(mp.mpc(ord(char), 0))
                stacktrace.write(f'inputed: {mp.nstr(stack[-1], 15)}\n')

    with open("trace.txt", "w", encoding="utf-8") as stacktrace:
        while 0 <= PC < len(program):
            inst = program[PC]
            execitr(inst)
            if debug:
                print(f"{PC} {inst} {format_stack(stack)}\n")
            stacktrace.write(f"{PC} {inst} {format_stack(stack)}\n")
            PC += 1
        print("\nprogram ended")

# Still allows you to run interpreter.py standalone if you ever want to
if __name__ == "__main__":
    fname = input("please input a file to load program: ")
    dbg = int(input("Enable debug mode?(1/0): "))
    run_program(fname, dbg)
    input("Press Enter to exit...")
