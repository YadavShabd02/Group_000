import sys

REG = [0] * 32
REG[2] = 380  # x2 = sp initialized to 380
PC = 0

memory_values = {
    f"0x000100{format(i, '02x')}": 0 for i in range(0x00, 0x80, 0x04)
}
MEMORY_KEYS = list(memory_values.keys())

def bin_to_dec(binary, signed=True):
    if not signed:
        return int(binary, 2)
    return int(binary, 2) - (2 ** len(binary)) if binary[0] == '1' else int(binary, 2)

def extract_fields(binary):
    return {
        'opcode': binary[25:],  # bits [6:0]
        'rd': int(binary[20:25], 2),
        'funct3': binary[17:20],
        'rs1': int(binary[12:17], 2),
        'rs2': int(binary[7:12], 2),
        'funct7': binary[0:7],
        'imm_i': bin_to_dec(binary[0:12]),
        'imm_b': bin_to_dec(binary[0] + binary[24] + binary[1:7] + binary[20:24] + '0'),
        'imm_s': bin_to_dec(binary[0:7] + binary[20:25]),
        'imm_j': bin_to_dec(binary[0] + binary[12:20] + binary[11] + binary[1:11] + '0')
    }

def handle_r_type(f):
    rs1, rs2, rd, funct3, funct7 = f['rs1'], f['rs2'], f['rd'], f['funct3'], f['funct7']
    if funct3 == '000': REG[rd] = REG[rs1] + REG[rs2] if funct7 == '0000000' else REG[rs1] - REG[rs2]
    elif funct3 == '010': REG[rd] = int(REG[rs1] < REG[rs2])
    elif funct3 == '101': REG[rd] = (REG[rs1] & 0xFFFFFFFF) >> (REG[rs2] % 32)
    elif funct3 == '110': REG[rd] = REG[rs1] | REG[rs2]
    elif funct3 == '111': REG[rd] = REG[rs1] & REG[rs2]

def handle_i_type(f):
    global PC
    rs1, rd, imm = f['rs1'], f['rd'], f['imm_i']
    if f['opcode'] == '0010011': REG[rd] = REG[rs1] + imm
    elif f['opcode'] == '1100111':
        temp = PC + 4
        PC = (REG[rs1] + imm) & ~1
        REG[rd] = temp
    elif f['opcode'] == '0000011':
        addr = REG[rs1] + imm
        REG[rd] = memory_values.get(f"0x{addr:08x}", 0)

def handle_s_type(f):
    rs1, rs2, imm = f['rs1'], f['rs2'], f['imm_s']
    addr = REG[rs1] + imm
    memory_values[f"0x{addr:08x}"] = REG[rs2] & 0xFFFFFFFF

def handle_j_type(f):
    global PC
    rd = f['rd']
    REG[rd] = PC + 4
    PC += f['imm_j']

def handle_b_type(f):
    rs1, rs2, imm = f['rs1'], f['rs2'], f['imm_b']
    if f['funct3'] == '000': return imm if REG[rs1] == REG[rs2] else 0
    elif f['funct3'] == '001': return imm if REG[rs1] != REG[rs2] else 0
    return 0

def handle_instruction(f):
    if f['opcode'] == '0110011': handle_r_type(f)
    elif f['opcode'] in ['0010011', '1100111', '0000011']: handle_i_type(f)
    elif f['opcode'] == '0100011': handle_s_type(f)
    elif f['opcode'] == '1101111': handle_j_type(f)

def dump_state(fout):
    fout.write(f"{PC} " + ' '.join(str(REG[i] & 0xFFFFFFFF) for i in range(32)) + "\n")

def dump_memory(fout):
    for addr in MEMORY_KEYS:
        fout.write(f"{addr}:{memory_values[addr]}\n")

def simulate(input_file, output_file):
    global PC, REG
    REG = [0] * 32
    REG[2] = 380
    PC = 0

    with open(input_file, 'r') as fin:
        instructions = [line.strip() for line in fin if line.strip()]
    with open(output_file, 'w') as fout:
        while PC < len(instructions) * 4:
            instr_index = PC // 4
            instr = instructions[instr_index]
            if instr == '00000000000000000000000001100011':  # HALT
                dump_state(fout)
                break

            f = extract_fields(instr)
            if f['opcode'] == '1100011':  # B-type (beq, bne)
                offset = handle_b_type(f)
                PC += offset if offset != 0 else 4
                dump_state(fout)
            else:
                handle_instruction(f)
                if f['opcode'] not in ['1100111', '1101111']:
                    PC += 4
                dump_state(fout)
        dump_memory(fout)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python mysim.py <input_file> <output_file>")
    else:
        simulate(sys.argv[1], sys.argv[2])
