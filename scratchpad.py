cpu.push(0xA9)   # LDA #0x0A
cpu.push(0x0A)

cpu.push(0x42)   # print_status

cpu.push(0x8D)   # STA $4401
cpu.push(0x01)
cpu.push(0x44)

cpu.push(0x42)   # print_status

cpu.push(0xA2)   # LDX #0x01
cpu.push(0x01)

cpu.push(0xBD)   # LDA #0x4400,X
cpu.push(0x00)
cpu.push(0x44)

cpu.push(0x42)   # print_status


# Test JMP
cpu.push(0x42)   # print_status

cpu.push(0xA9)   # LDA 0x0D LSB 0x100D
cpu.push(0x0D)

cpu.push(0x8D)   # STA 0x2000
cpu.push(0x00)
cpu.push(0x20)

cpu.push(0xA9)   # LDA 0x10 MSB 0x100D
cpu.push(0x10)

cpu.push(0x8D)      # STA 0x2001
cpu.push(0x01)
cpu.push(0x20)

cpu.push(0xA9)   # LDA 0x02
cpu.push(0x02)

cpu.push(0xAA)  # TAX
cpu.push(0xCA)  # DEX   loc 0x100D

cpu.push(0x42)  #DBG
cpu.push(0x6C)  #JMP

# JMP to address 2000
cpu.push(0x00)  # LSB
cpu.push(0x20)  # MSB

# TEST BMI
cpu.push(0xA9) # LDA #0x90
cpu.push(0x90)  # value > 80 set N

cpu.push(0xC9) # CMP #0x01
cpu.push(0x01)

cpu.push(0x42)  # DBG

cpu.push(0x30)  # BMI LDX #0xFF
cpu.push(0x03)  # Jump 2 byte ahead

cpu.push(0xA2)  # LDX #0x01
cpu.push(0x01)  # 

cpu.push(0x42)  # DBG

cpu.push(0xA2)  # LDX #0xFF
cpu.push(0xFF)  # 

cpu.push(0x42)  # DBG


#
pu.push(0xA2)  # LDX #0xFF
cpu.push(0xFF)  # 

cpu.push(0x42)  # DBG

cpu.push(0xA9) # LDA #0x90
cpu.push(0x90)  # value >= 80 set N

cpu.push(0xC9) # CMP #0x01
cpu.push(0x01)

cpu.push(0x42)  # DBG

cpu.push(0xF0)  # BEQ LDX #0xF6
cpu.push(0xF6)  # 

cpu.push(0xA2)  # LDX #0x01
cpu.push(0x01)  # 

cpu.push(0x42)  # DBG

# PHA
cpu.push(0xA9)   # LDA #0x0A
cpu.push(0x0A)

cpu.push(0x48)   # PHA

cpu.push(0x42)   # DBG

cpu.push(0xAE) # LDX 0x1FF
cpu.push(0xFF)
cpu.push(0x01)

cpu.push(0x42)   # DBG

cpu.push(0xA9)   # LDA #0x0A
cpu.push(0x00
         )
cpu.push(0x42)   # DBG

cpu.push(0x68)   # PLA

cpu.push(0x42)   # DBG


# JSR/RTS
cpu.push(0x20)      # JSR $1008
cpu.push(0x08)
cpu.push(0x10)

cpu.push(0x42)      # DBG

cpu.push(0xA0)      # LDY #$02
cpu.push(0x02)

cpu.push(0x42)      # DBG

cpu.push(0)         # HALT ON ERROR

cpu.push(0xA9)      # LDA #0x0A     (HERE JSR COMMAND jump)
cpu.push(0x00)

cpu.push(0xA2)      # LDX #$01
cpu.push(0x01)

cpu.push(0x60)      # RTS

# ADC

cpu.push(0xA9)      # LDA #0xF0
cpu.push(0xF0)

#cpu.push(0x38) # SEC

cpu.push(0x69)      # ADC #0x01
cpu.push(0x01)

cpu.push(0x42)      # DBG

# ADC

cpu.push(0xA9)      # LDA #0xF0
cpu.push(0xF0)

cpu.push(0x42)      # DBG

cpu.push(0x38) # SEC

cpu.push(0x42)      # DBG

cpu.push(0x69)      # ADC #0x01
cpu.push(0x01)

cpu.push(0x42)      # DBG

# SBC

cpu.push(0xA9)      # LDA #0xXX
cpu.push(0x01)

cpu.push(0x42)      # DBG

cpu.push(0x38)      # SEC

cpu.push(0x42)      # DBG

cpu.push(0xE9)      # SBC #0xXX
cpu.push(0x01)

cpu.push(0x42)      # DBG


# SBC

cpu.push(0xA9)      # LDA #0xXX
cpu.push(0x01)

cpu.push(0x42)      # DBG

cpu.push(0xEA)      # NOP
cpu.push(0xEA)      # NOP
cpu.push(0xEA)      # NOP
cpu.push(0xEA)      # NOP
cpu.push(0xEA)      # NOP
cpu.push(0xEA)      # NOP


cpu.push(0x42)      # DBG

cpu.push(0x38)      # SEC

cpu.push(0x42)      # DBG

cpu.push(0xE9)      # SBC #0xXX
cpu.push(0x02)

cpu.push(0x42)      # DBG

# TO DO
# CPX, CPY, DEC, INC

