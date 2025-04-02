import sys

# Global registers and PC
REG = [0] * 32
REG[2] = 380  # x2 = sp initialized to 380
PC = 0

# Original memory initialization
ORIG_MEMORY = {
    "0x00010000": 0, "0x00010004": 0, "0x00010008": 0, "0x0001000C": 0,
    "0x00010010": 0, "0x00010014": 0, "0x00010018": 0, "0x0001001C": 0,
    "0x00010020": 0, "0x00010024": 0, "0x00010028": 0, "0x0001002C": 0,
    "0x00010030": 0, "0x00010034": 0, "0x00010038": 0, "0x0001003C": 0,
    "0x00010040": 0, "0x00010044": 0, "0x00010048": 0, "0x0001004C": 0,
    "0x00010050": 0, "0x00010054": 0, "0x00010058": 0, "0x0001005C": 0,
    "0x00010060": 0, "0x00010064": 0, "0x00010068": 0, "0x0001006C": 0,
    "0x00010070": 0, "0x00010074": 0, "0x00010078": 0, "0x0001007C": 0
}
ORIG_MEMORY_KEYS = list(ORIG_MEMORY.keys())
memory_values = ORIG_MEMORY.copy()

def bin_to_dec(binary, signed=True):
    if not signed:
        return int(binary, 2)
    if binary[0] == '1':
        return int(binary, 2) - (1 << len(binary))
    return int(binary, 2)

def dec_to_bin(val, bits=32):
    if val < 0:
        val = (1 << bits) + val
    return format(val, f'0{bits}b')

def extract_fields(binary):
    fields = {
        'opcode': binary[25:],            # bits [6:0]
        'rd': int(binary[20:25], 2),        # bits [11:7]
        'funct3': binary[17:20],           # bits [14:12]
        'rs1': int(binary[12:17], 2),       # bits [19:15]
        'rs2': int(binary[7:12], 2),        # bits [24:20]
        'funct7': binary[0:7],             # bits [31:25]
        'imm_i': bin_to_dec(binary[0:12]),
        'imm_b': bin_to_dec(binary[0] + binary[24] + binary[1:7] + binary[20:24] + '0', signed=True),
        'imm_s': bin_to_dec(binary[0:7] + binary[20:25], signed=True),
        'imm_j': bin_to_dec(binary[0] + binary[12:20] + binary[11] + binary[1:11] + '0', signed=True)
    }
    return fields

def handle_r_type(fields):
    rs1, rs2, rd = fields['rs1'], fields['rs2'], fields['rd']
    funct3, funct7 = fields['funct3'], fields['funct7']
    result = 0
    if funct3 == '000' and funct7 == '0000000':  # add
        result = REG[rs1] + REG[rs2]
    elif funct3 == '000' and funct7 == '0100000':  # sub
        result = REG[rs1] - REG[rs2]
    elif funct3 == '010':  # slt
        result = int(REG[rs1] < REG[rs2])
    elif funct3 == '101':  # srl
        result = (REG[rs1] & 0xFFFFFFFF) >> (REG[rs2] & 0x1F)
    elif funct3 == '110':  # or
        result = REG[rs1] | REG[rs2]
    elif funct3 == '111':  # and
        result = REG[rs1] & REG[rs2]
    if rd != 0:
        REG[rd] = result & 0xFFFFFFFF

def handle_special_instructions(fields):
    """
    Handle bonus instructions that are not standard.
    In this version we only implement:
      - rst: reset registers (opcode '1110011', funct3 '000', funct7 '0000000')
      - halt: stop simulation (opcode '1110011', funct3 '001', funct7 '0000000')
    """
    global PC
    opcode = fields['opcode']
    funct3 = fields['funct3']
    funct7 = fields['funct7']
    if opcode == '1110011' and funct3 == '000' and funct7 == '0000000':
        # Reset all registers except x0 (which is always 0)
        for i in range(1, 32):
            REG[i] = 0
    elif opcode == '1110011' and funct3 == '001' and funct7 == '0000000':
        # Halt execution by setting PC high enough to break the simulation loop
        PC = 999999999

def handle_i_type(fields):
    global PC
    rs1, rd = fields['rs1'], fields['rd']
    imm = fields['imm_i']
    if fields['opcode'] == '0010011':  # addi
        if rd != 0:
            REG[rd] = (REG[rs1] + imm) & 0xFFFFFFFF
    elif fields['opcode'] == '1100111':  # jalr
        temp = PC + 4
        PC = (REG[rs1] + imm) & ~1
        if rd != 0:
            REG[rd] = temp & 0xFFFFFFFF
    elif fields['opcode'] == '0000011':  # lw
        address = REG[rs1] + imm
        key = f"0x{address:08x}"
        val = memory_values.get(key, 0)
        if rd != 0:
            REG[rd] = val & 0xFFFFFFFF

def handle_s_type(fields):
    rs1, rs2 = fields['rs1'], fields['rs2']
    imm = fields['imm_s']
    address = REG[rs1] + imm
    key = f"0x{address:08x}"
    memory_values[key] = REG[rs2] & 0xFFFFFFFF

def handle_j_type(fields):
    global PC
    rd = fields['rd']
    link_val = PC + 4
    PC = PC + fields['imm_j']
    if rd != 0:
        REG[rd] = link_val & 0xFFFFFFFF

def handle_b_type(fields):
    rs1, rs2 = fields['rs1'], fields['rs2']
    imm = fields['imm_b']
    if fields['funct3'] == '000':  # beq
        return imm if REG[rs1] == REG[rs2] else 0
    elif fields['funct3'] == '001':  # bne
        return imm if REG[rs1] != REG[rs2] else 0
    return 0

def handle_instruction(fields):
    opcode = fields['opcode']
    if opcode == '0110011':       # R-type
        handle_r_type(fields)
    elif opcode in ['0010011', '1100111', '0000011']:  # I-type
        handle_i_type(fields)
    elif opcode == '0100011':     # S-type
        handle_s_type(fields)
    elif opcode == '1101111':     # J-type
        handle_j_type(fields)
    else:
        # Check for our custom bonus instructions (rst/halt)
        handle_special_instructions(fields)

def dump_state(fout):
    fout.write(f"{PC} " + " ".join(str(REG[i] & 0xFFFFFFFF) for i in range(32)) + "\n")

def dump_state_binary(fout):
    fout.write("0b" + dec_to_bin(PC) + " " +
               " ".join("0b" + dec_to_bin(REG[i] & 0xFFFFFFFF) for i in range(32)) + "\n")

def dump_memory(fout):
    for key in ORIG_MEMORY_KEYS:
        fout.write(f"{key}:{memory_values[key]}\n")

def dump_memory_binary(fout):
    for key in ORIG_MEMORY_KEYS:
        fout.write(f"{key}:0b" + dec_to_bin(memory_values[key]) + "\n")

def simulate(input_file, output_file_decimal, output_file_binary):
    global PC, REG, memory_values
    REG = [0] * 32
    REG[2] = 380
    PC = 0
    memory_values = ORIG_MEMORY.copy()

    with open(input_file, 'r') as fin:
        instructions = [line.strip() for line in fin if line.strip()]

    with open(output_file_decimal, 'w') as fout_dec, open(output_file_binary, 'w') as fout_bin:
        while PC < len(instructions) * 4:
            instr = instructions[PC // 4]
            # Check for the existing HALT instruction (if present)
            if instr == '00000000000000000000000001100011':
                dump_state(fout_dec)
                dump_state_binary(fout_bin)
                break

            fields = extract_fields(instr)
            if fields['opcode'] == '1100011':  # B-type branch
                offset = handle_b_type(fields)
                if offset == 0:
                    PC += 4
                else:
                    PC += offset
                if PC // 4 < len(instructions) and instructions[PC // 4] == '00000000000000000000000001100011':
                    dump_state(fout_dec)
                    dump_state_binary(fout_bin)
                    break
                dump_state(fout_dec)
                dump_state_binary(fout_bin)
            else:
                handle_instruction(fields)
                if fields['opcode'] not in ['1100111', '1101111']:
                    PC += 4
                dump_state(fout_dec)
                dump_state_binary(fout_bin)

        dump_memory(fout_dec)
        dump_memory_binary(fout_bin)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python mysim.py <input_file> <decimal_output_file> <binary_output_file>")
    else:
        simulate(sys.argv[1], sys.argv[2], sys.argv[3])
