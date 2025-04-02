import sys


def sign_extend(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val


def simulate(lines):
    inst_mem = [l.strip() for l in lines if l.strip() != ""]
    reg = [0] * 32
    reg[2] = 380
    mem = {}
    trace = []
    pc = 4


    while True:
        idx = (pc // 4) - 1
        if idx < 0 or idx >= len(inst_mem):
            break
        inst = int(inst_mem[idx], 2)
        opcode = inst & 0x7F
        
        if opcode == 0x33:
            rd = (inst >> 7) & 0x1F
            funct3 = (inst >> 12) & 0x7
            rs1 = (inst >> 15) & 0x1F
            rs2 = (inst >> 20) & 0x1F
            funct7 = (inst >> 25) & 0x7F
            if funct3 == 0x0 and funct7 == 0x00:
                reg[rd] = (reg[rs1] + reg[rs2]) & 0xFFFFFFFF
            elif funct3 == 0x0 and funct7 == 0x20:
                reg[rd] = (reg[rs1] - reg[rs2]) & 0xFFFFFFFF
            elif funct3 == 0x1 and funct7 == 0x00:
                shamt = reg[rs2] & 0x1F
                reg[rd] = (reg[rs1] << shamt) & 0xFFFFFFFF
            elif funct3 == 0x2 and funct7 == 0x00:
                reg[rd] = 1 if (reg[rs1] & 0xFFFFFFFF) < (reg[rs2] & 0xFFFFFFFF) else 0
            pc += 4
        elif opcode == 0x13:
            rd = (inst >> 7) & 0x1F
            funct3 = (inst >> 12) & 0x7
            rs1 = (inst >> 15) & 0x1F
            imm = sign_extend((inst >> 20) & 0xFFF, 12)
            if funct3 == 0x0:
                reg[rd] = (reg[rs1] + imm) & 0xFFFFFFFF
            elif funct3 == 0x3:
                reg[rd] = 1 if (reg[rs1] & 0xFFFFFFFF) < (imm & 0xFFFFFFFF) else 0
            pc += 4
        elif opcode == 0x63:
            funct3 = (inst >> 12) & 0x7
            rs1 = (inst >> 15) & 0x1F
            rs2 = (inst >> 20) & 0x1F
            imm = (((inst >> 31) & 0x1) << 12) | (((inst >> 7) & 0x1) << 11) | (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1)
            imm = sign_extend(imm, 13)
            if funct3 == 0x0:
                if rs1 == 0 and rs2 == 0 and imm == 0:
                    trace.append(" ".join(str(x) for x in ([pc] + reg)))
                    break
                if reg[rs1] == reg[rs2]:
                    pc = pc + imm
                else:
                    pc += 4
            else:
                pc += 4
        elif opcode == 0x03:
            rd = (inst >> 7) & 0x1F
            funct3 = (inst >> 12) & 0x7
            rs1 = (inst >> 15) & 0x1F
            imm = sign_extend((inst >> 20) & 0xFFF, 12)
            addr = (reg[rs1] + imm) & 0xFFFFFFFF
            if funct3 == 0x2:
                reg[rd] = mem.get(addr, 0)
            pc += 4
        elif opcode == 0x23:
            imm = (((inst >> 25) & 0x7F) << 5) | ((inst >> 7) & 0x1F)
            imm = sign_extend(imm, 12)
            rs1 = (inst >> 15) & 0x1F
            rs2 = (inst >> 20) & 0x1F
            addr = (reg[rs1] + imm) & 0xFFFFFFFF
            addr = addr & ~0x3
            funct3 = (inst >> 12) & 0x7
            if funct3 == 0x2:
                mem[addr] = reg[rs2]
            pc += 4
        else:
            pc += 4
        reg[0] = 0
        trace.append(" ".join(str(x) for x in ([pc] + reg)))
    return trace, mem
def main():
    inp = sys.argv[1]
    out = sys.argv[2]
    with open(inp, "r") as f:
        lines = f.readlines()
    t, m = simulate(lines)
    with open(out, "w") as f:
        for l in t:
            f.write(l + "\n")
        for addr in range(0, 32 * 4, 4):
            val = m.get(addr, 0)
            f.write("0x" + format(addr, "08X") + ":" + format(val & 0xFFFFFFFF, "032b") + "\n")
if __name__ == "__main__":
    main()
