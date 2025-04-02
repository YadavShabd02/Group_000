import sys

# Global registers and PC
REG = [0] * 32
REG[2] = 380  # x2 = sp initialized to 380
PC = 0

# Original memory initialization (addresses as lowercase keys)
ORIG_MEMORY = {
    "0x00010000": 0, "0x00010004": 0, "0x00010008": 0, "0x0001000c": 0,
    "0x00010010": 0, "0x00010014": 0, "0x00010018": 0, "0x0001001c": 0,
    "0x00010020": 0, "0x00010024": 0, "0x00010028": 0, "0x0001002c": 0,
    "0x00010030": 0, "0x00010034": 0, "0x00010038": 0, "0x0001003c": 0,
    "0x00010040": 0, "0x00010044": 0, "0x00010048": 0, "0x0001004c": 0,
    "0x00010050": 0, "0x00010054": 0, "0x00010058": 0, "0x0001005c": 0,
    "0x00010060": 0, "0x00010064": 0, "0x00010068": 0, "0x0001006c": 0,
    "0x00010070": 0, "0x00010074": 0, "0x00010078": 0, "0x0001007c": 0
}
ORIG_MEMORY_KEYS = list(ORIG_MEMORY.keys())
memory_values = ORIG_MEMORY

def bin_to_dec(binary, signed=True):
    if not signed:
        return int(binary, 2)
    if binary[0] == '1':
        return int(binary, 2) - (2 ** len(binary))
    return int(binary, 2)

def dec_to_bin(val, bits=32):
    if val < 0:
        val = (2 ** bits) + val
    return format(val, f'0{bits}b')

def extract_fields(binary):
    fields = {
        'opcode': binary[25:],            # bits [6:0]
        'rd': int(binary[20:25], 2),        # bits [11:7]
        'funct3': binary[17:20],           # bits [14:12]
        'rs1': int(binary[12:17], 2),       # bits [19:15]
        'rs2': int(binary[7:12], 2),        # bits [24:20]
        'funct7': binary[0:7],             # bits [31:25]
        'imm_i': bin_to_dec(binary[0:12]),  # I-type immediate
        'imm_b': bin_to_dec(binary[0] + binary[24] + binary[1:7] + binary[20:24] + '0', signed=True)
    }
    fields['imm_s'] = bin_to_dec(binary[0:7] + binary[20:25], signed=True)
    fields['imm_j'] = bin_to_dec(binary[0] + binary[12:20] + binary[11] + binary[1:11] + '0', signed=True)
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
        shift_amount = REG[rs2] & 0x1F
        result = (REG[rs1] & 0xFFFFFFFF) >> shift_amount
    elif funct3 == '110':  # or
        result = REG[rs1] | REG[rs2]
    elif funct3 == '111':  # and
        result = REG[rs1] & REG[rs2]
    if rd != 0:
        REG[rd] = result

def handle_i_type(fields):
    global PC
    rs1, rd = fields['rs1'], fields['rd']
    imm = fields['imm_i']
    if fields['opcode'] == '0010011':  # addi
        if rd != 0:
            REG[rd] = REG[rs1] + imm
    elif fields['opcode'] == '1100111':  # jalr
        temp = PC + 4
        PC = (REG[rs1] + imm) & ~1
        if rd != 0:
            REG[rd] = temp
    elif fields['opcode'] == '0000011':  # lw
        address = REG[rs1] + imm
        key = f"0x{address:08x}"
        val = memory_values.get(key, 0)
        if rd != 0:
            REG[rd] = val

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
        REG[rd] = link_val

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
    if opcode == '0110011':  # R-type
        handle_r_type(fields)
    elif opcode in ['0010011', '1100111', '0000011']:  # I-type
        handle_i_type(fields)
    elif opcode == '0100011':  # S-type
        handle_s_type(fields)
    elif opcode == '1101111':  # J-type (jal)
        handle_j_type(fields)
    # B-type handled in main loop

def dump_state(fout):
    fout.write(f"{PC} " + " ".join(str(REG[i] & 0xFFFFFFFF) for i in range(32)) + "\n")

def dump_memory(fout):
    for key in ORIG_MEMORY_KEYS:
        fout.write(f"{key}:{memory_values[key]}\n")

def simulate(input_file, output_file):
    global PC, REG
    REG = [0] * 32
    REG[2] = 380
    PC = 0

    with open(input_file, 'r') as fin:
        instructions = [line.strip() for line in fin if line.strip()]

    with open(output_file, 'w') as fout:
        while PC < len(instructions)*4:
            # Check if current instruction is HALT; if so, dump final state twice and break.
            if instructions[PC//4] == '00000000000000000000000001100011':
                dump_state(fout)
                break

            fields = extract_fields(instructions[PC//4])
            if fields['opcode'] == '1100011':  # Branch (B-type)
                offset = handle_b_type(fields)
                if offset == 0:
                    PC += 4
                else:
                    PC += offset
                # If after branch PC now points to HALT, perform HALT handling immediately.
                if instructions[PC//4] == '00000000000000000000000001100011':
                    dump_state(fout)
                    break
                else:
                    dump_state(fout)
            else:
                handle_instruction(fields)
                if fields['opcode'] not in ['1101111', '1100111']:
                    PC += 4
                dump_state(fout)

        dump_memory(fout)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python mysim.py <input_file> <output_file>")
    else:
        simulate(sys.argv[1], sys.argv[2])
