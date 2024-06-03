import sys
import traceback


# opcode 0xYZ corresponds to list value opcodes[X][Y]
opcodes = [
    ['call', 'jmpi', 'inv', 'lbdu', 'addi', 'stb', 'br', 'ldb', 'cmpgei', 'inv', 'inv', 'ldhu', 'andi', 'sth', 'bge', 'ldh'],
    ['cmplti', 'inv', 'inv', 'initda', 'ori', 'stw', 'blt', 'ldw', 'cmpnei', 'inv', 'inv', 'flushda', 'xori', 'inv', 'bne', 'inv'],
    ['cmpeqi', 'inv', 'inv', 'ldbuio', 'muli', 'stbio', 'beq', 'ldbio', 'cmpgeui', 'inv', 'inv', 'ldhuio', 'andhi', 'sthio', 'bgeu', 'ldhio'],
    ['compltui', 'inv', 'custom', 'initd', 'orhi', 'stwio', 'bltu', 'ldwio', 'rdprs', 'inv', 'R-type', 'flushd', 'xorhi', 'inv', 'inv', 'inv']
]

opxcodes = [
    ['inv', 'eret', 'roli', 'rol', 'flushp', 'ret', 'nor', 'mulxuu', 'cmpge', 'bret', 'inv', 'ror', 'flushi', 'jmp', 'and', 'inv'],
    ['cmplt', 'inv', 'slli', 'sll', 'wrprs', 'inv', 'or', 'mulxsu', 'cmpne', 'inv', 'srli', 'srl', 'nextpc', 'callr', 'xor', 'mulxss'],
    ['cmpeq', 'inv', 'inv', 'inv', 'divu', 'div', 'rdctl', 'mul', 'cmpgeu', 'initi', 'inv', 'inv', 'inv', 'trap', 'wrctl', 'inv'],
    ['cmpltu', 'add', 'inv', 'inv', 'break', 'inv', 'break', 'inv', 'sync', 'inv', 'inv', 'sub', 'srai', 'sra', 'inv', 'inv', 'inv', 'inv']
]

pseudos = [
    'bgt',
    'bgtu',
    'ble',
    'bleu',
    'cmpgt',
    'cmpgti',
    'cmpgtu',
    'cmpgtui',
    'cmple',
    'cmplei',
    'cmpleu',
    'cmpleui',
    'mov',
    'movhi',
    'movi',
    'movia',
    'movui',
    'nop',
    'subi']

def parse_macros(macro: str, label: str) -> str:
    """
    Parses assembler macros and returns the output of the equivalent operation.
    """
    retval = label[2:]
    retval = '0'*(32-len(retval)) + retval
    retval = int(retval, 2)

    match macro:
        case '%lo':
            retval = retval & 0xFFFF
        case '%hi':
            retval = (retval >> 16) & 0xFFFF
        case '%hiadj':
            retval = ((retval >> 16) & 0xFFFF) + ((retval >> 15) & 0x1)
        case '%gprel':
           print ("UH OH") 
        
    return bin(retval)

def convert_pseudo(instr: str) -> str:
    """
    Converts a pseudo-instruction into its regular form, and passes it to its equivalent form.
    """
    old_instr = instr
    instrs = instr.split(" ")

    swap_ab_i = 0
    swap_ab_r = 0

    # if immediate, convert to binary
    if 'r' not in instrs[-1]:
        if 'x' in instrs[-1]:
            instrs[-1] = bin(int(instrs[-1], 16))
        elif 'b' not in instrs[-1]:
            instrs[-1] = bin(int(instrs[-1]))

    match instrs[0]:
        case 'bgt':
            instrs[0] = 'blt'
            swap_ab_i = 1
        case 'bgtu':
            instrs[0] = 'bltu'
            swap_ab_i = 1
        case 'ble':
            instrs[0] = 'bge'
            swap_ab_i = 1
        case 'bleu':
            instrs[0] = 'bgeu'
            swap_ab_i = 1
        case 'cmpgt':
            instrs[0] = 'cmplt'
            swap_ab_r = 1
        case 'cmpgti':
            instrs[0] = 'cmpgei'
            instrs[-1] = str(int(instrs[-1]) + 1) 
        case 'cmpgtu':
            instrs[0] = 'cmpltu '
            swap_ab_r = 1
        case 'cmpgtui': 
            instrs[0] = 'cmpgeui'
            instrs[-1] = str(int(instrs[-1]) + 1) 
        case 'cmple': 
            instrs[0] = 'cmpge'
            swap_ab_r = 1
        case 'cmplei': 
            instrs[0] = 'cmplti'
            instrs[-1] = str(int(instrs[-1]) + 1) 
        case 'cmpleu': 
            instrs[0] = 'cmpgeu'
            swap_ab_r = 1
        case 'cmpleui': 
            instrs[0] = 'cmpltui'
            instrs[-1] = str(int(instrs[-1]) + 1) 
        case 'mov': 
            instrs[0] = 'add'
            instrs.append('r0')
        case 'movhi': 
            instrs[0] = 'orhi'
            instrs.insert(2, 'r0')
        case 'movi': 
            instrs[0] = 'addi'
            instrs.insert(2, 'r0')
        case 'movia':
            return [
                f"orhi {instrs[1]} r0 {parse_macros('%hiadj', instrs[-1])}",
                f"addi {instrs[1]} r0 {parse_macros('%lo', instrs[-1])}"
            ]
        case 'movui': 
            instrs[0] = 'ori'
            instrs.insert(2, 'r0')
        case 'nop': 
            return 'add r0 r0 r0'
        case 'subi': 
            instrs[0] = 'addi'
            instrs[-1] = '-' + instrs[-1]
    
    if swap_ab_r:
        temp = instrs.pop(2)
        instrs.insert(3, temp)
    elif swap_ab_i:
        temp = instrs.pop(1)
        instrs.insert(2, temp)

    return " ".join(instrs)

def binary_to_nios(instr: str) -> str:
    """
    Converts a 32-bit binary integer to a Nios II assembly instruction.
    """
    # remove '0b'
    instr = instr[2:]
    # find opcode
    op_row = int(instr[-6:-4], 2)
    op_col = int(instr[-4:], 2)
    op = opcodes[op_row][op_col]
    
    if op == 'R-type': #r-type - find opx
        # opx = instr[16:11]
        opx_row = int(instr[-17:-15], 2)
        opx_col = int(instr[-15:-11], 2)
        opx = opxcodes[opx_row][opx_col]
        a = int(instr[0:5], 2)
        b = int(instr[5:10], 2)
        c = int(instr[10:15], 2) 

        return f"{opx} r{a} r{b} r{c}"

    elif op in ['jmpi', 'call']:
        imm = hex(int(instr[:-6], 2) * 4)

        return f"{op} {imm}"
    else: #i-type
        a = int(instr[0:5], 2)
        b = int(instr[5:10], 2)
        imm = hex(int(instr[10:-6], 2))

        return f"{op} r{a} r{b} {imm}"

def nios_convert(instr: str) -> str:
    """
    Converts a Nios II assembly instruction to both binary and hexadecimal.
    """
    r = 0
    i = 0
    j = 0
    instr_b = []

    if instr.count('r') == 2:
        i = 1
    elif instr.count('r') == 3:
        r = 1
    else:
        j = 1

    operands = instr.split(" ")
    instr = operands.pop(0)


    if j:
        print("\n[IMPORTANT] Ensure that top 4 bits of PC and target are the same")
        # check encoding of immediate
        if 'x' in operands[0]:
            imm = int(operands[0], 16)
        elif 'b' in operands[0]:
            imm = int(operands[0], 2)
        else:
            imm = int(operands[0])

        op = '000000' if instr == 'call' else '000001'

        imm = bin(imm)[2:]
        imm = '0'*(26 - len(imm)) + imm
        imm = imm[3:-2]
        # j-type: imm[26] op[6]
        instr_b = [imm, op]
    # instr b, a, imm
    elif i:
        # find opcode
        for i in range (4):
            for j in range(16):
                if opcodes[i][j] == instr:
                    op = bin(int(f"{i}{j}", 16))[2:]

        # convert operands to integers
        b = operands[0][2:] if '$' in operands[0] else operands[0][1:]
        b = int(b)
        a = operands[1][2:] if '$' in operands[1] else operands[1][1:]
        a = int(a)

        # check encoding of immediate
        if 'x' in operands[2]: 
            imm = int(operands[2][2:], 16)
        elif 'b' in operands[2]:
            imm = int(operands[2][2:], 2)
        else:
            imm = int(operands[2]) 
        
        # convert all to binary
        a = bin(a)[2:]
        b = bin(b)[2:]
        imm = bin(imm)[2:]

        # ensure correct length
        a = '0'*(5-len(a)) + a
        b = '0'*(5-len(b)) + b
        imm = '0'*(16-len(imm)) + imm
        op = '0'*(6-len(op)) + op

        # i-type: a[5] b[5] imm[16] op[6]
        instr_b = [a, b, imm, op]
    
    # instr c, a, b
    elif r:
        op = int('0x3A', 16)
        for i in range(4):
            for j in range(16):
                if opxcodes[i][j] == instr:
                    opx = int(f"{i}{j}", 16)

        a = operands[1][2:] if '$' in operands[1] else operands[1][1:]
        a = bin(int(a))[2:]
        b = operands[2][2:] if '$' in operands[0] else operands[2][1:]
        b = bin(int(b))[2:]
        c = operands[0][2:] if '$' in operands[2] else operands[0][1:]
        c = bin(int(c))[2:]
        
        opx = bin(opx)[2:]
        op = bin(op)[2:]

        # ensure correct length
        a = '0'*(5-len(a)) + a
        b = '0'*(5-len(b)) + b
        c = '0'*(5-len(c)) + c
        opx = opx + '0'*(11-len(opx)) # pad to the right
        op = '0'*(6-len(op)) + op
    
        # r-type: a[5] b[5] c[5] opx[11] op[6]
        instr_b = [a, b, c, opx, op]

    instr_h = hex(int("".join(instr_b), 2))
    instr_b = " ".join(instr_b)
    return [instr_b, instr_h]


if __name__ == '__main__':
        
    print('-----------------------------------------------------------------')
    print("Welcome to the Nios II decompiler, written by Ethan Liberman.")
    print('-----------------------------------------------------------------')
    while (choice := input("Choose conversion: [0] for machine to Nios, [1] for Nios to machine, or [q] to quit: ")) != 'q':
        try:
            if int(choice) == 0:
                instr = input("Input instruction, with either an '0x...' for hex or '0b...' for binary: ")
                if instr[:2] == '0x':
                    instr = str(bin(int(instr, 16))) # convert to binary

                retval = f"NIOS: {binary_to_nios(instr)}"
            elif int(choice) == 1:
                print("Input instruction WITHOUT commas with a single space between operands.")
                print("If instruction uses a label, replace with PC value.")
                instr = input()
                if instr.split(" ")[0] in pseudos:
                    instr = convert_pseudo(instr)
                    if type(instr) == list:
                        print(instr)
                        ret1 = nios_convert(instr[0])
                        ret2 = nios_convert(instr[1])
                        retval = f"BIN:  {ret1[0]}\nHEX:  {ret1[1]}\nBIN:  {ret2[0]}\nHEX:  {ret2[1]}"
                        break
                
                retval = nios_convert(instr)
                retval = f"BIN:  {retval[0]}\nHEX:  {retval[1]}"
            else:
                raise ValueError

        except Exception:
            print("[ERROR] Please choose a valid option: [0]/[1]/[q]")
            print(traceback.format_exc())
            continue

        print(f"\nORIG: {instr}\n{retval}\n")
