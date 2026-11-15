import math
import cmath
def load_program(filename: str) -> list[str]:
    valid_instructions = {"1", "e", "j","c"}
    with open(filename, "r", encoding="utf-8") as file:
        content = file.read()
    return [char for char in content if char in valid_instructions]
filename = input("please input a file to load program: ")
program = load_program(filename)
stack = []
PC = 0

def safe_exp(x: complex) -> complex:
    if x.real == float('inf'):
        return complex(float('inf'), 0.0) if x.imag == 0 else complex(float('nan'), float('nan'))
    if x.real == float('-inf'):
        return 0j
    try:
        return cmath.exp(x)
    except OverflowError:
        if x.imag == 0:
            return complex(float('inf'), 0.0)
        return complex(float('nan'), float('nan'))
    except ValueError:
        return complex(float('nan'), float('nan'))

def safe_log(y: complex) -> complex:
    if y == 0j:
        return complex(float('-inf'), 0.0)
    try:
        return cmath.log(y)
    except ValueError:
        return complex(float('nan'), float('nan'))

def eml(x: complex, y: complex) -> complex:
    return safe_exp(y) - safe_log(x)


def execitr(instruction):
    if instruction=="1": #put 1
        stack.append((1+0j))
    elif instruction=="e": #do eml
        stack[-1]=eml(stack[-1],stack[-2])
        stack.pop(-2)
    elif instruction=="j": #jump if 1
        global PC
        if round(stack[-1].real) == 1:
            PC = round(stack[-1].imag)
    elif instruction == "c": # call sys instructions
        if round(stack[-1].imag) == 1: # input
            stack.append(complex(input()))
        elif round(stack[-1].imag) == 2:#output
            print(stack[-1].real)
while True:
    try:
        execitr(program[PC])
        print(str(PC)+" "+str(stack))
        PC+=1
    except:
        print("program ended")
        break
        
