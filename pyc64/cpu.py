# 6502 CPU Emulator
# By @TokyoEdtech
# REF: http://www.6502.org/tutorials/6502opcodes.html
from .bus import Bus
from .opcodes import get_opcode_definitions, CYCLE_COUNTS, INSTRUCTION_INCREMENTS, Mode
import json
import sys


class CPU:

    def __init__(self, bus: Bus):
        self.bus = bus
        self.a = 0x00
        self.x = 0x00
        self.y = 0x00
        self.pc = 0x1000
        self.sp = 0xFF

        self.irq_pending = False
        self.nmi_pending = False
        self.cycles_remaining = 0
        self.breakpoints = set()
        self.total_cycles = 0
        self.tracing = False
        self.trace_file = None
        self.auto_dasm_on_break = True


        self.n = False   # N - Negative flag
        self.v = False   # V - Overflow
        self.b = False   # B - Break
        self.d = False   # D - Decimal  
        self.i = False   # I - Interrupt
        self.z = False   # Z - Zero
        self.c = False   # C - Carry
        
        self.commands = get_opcode_definitions(self)
        self.cycles = CYCLE_COUNTS
        self.increments = INSTRUCTION_INCREMENTS

    def tick(self):
        # The VIC-II clock is synchronized with the CPU clock
        self.bus.vic.tick()
        
        # Check for badlines and adjust cycle count
        if self.bus.vic.is_badline():
            stolen_cycles = self.bus.vic.get_cycles_stolen()
            self.cycles_remaining -= stolen_cycles


        # Clock the CIA chips
        self.bus.cia1.tick()
        self.bus.cia2.tick()

        # Handle interrupts before doing anything else
        if self.nmi_pending:
            self.handle_nmi()
        
        if self.irq_pending and not self.i:
            self.handle_irq()

        # KERNAL LOAD trap for HLE of disk drive
        if self.pc == 0xFFD5:
            if self.handle_kernal_load():
                return # Skip normal instruction execution
        
        # KERNAL SAVE trap for HLE of disk drive
        if self.pc == 0xFFD8:
            if self.handle_kernal_save():
                return # Skip normal instruction execution

        command = self.bus.read(self.pc)

        # If we are at a breakpoint, enter the debugger
        if self.pc in self.breakpoints:
            self.debug_prompt()

        if self.cycles_remaining > 0:
            self.cycles_remaining -= 1
            return # Wait for next tick

        # --- Fetch and Execute New Instruction ---
        # Fetch command
        command = self.bus.read(self.pc)

        if self.tracing and self.trace_file:
            status = f"A:{self.a:02X} X:{self.x:02X} Y:{self.y:02X} PC:{self.pc:04X} SP:{self.sp:02X}"
            flags = f"  Flags: {'N' if self.n else '-'} {'V' if self.v else '-'} {'B' if self.b else '-'} {'D' if self.d else '-'} {'I' if self.i else '-'} {'Z' if self.z else '-'} {'C' if self.c else '-'}"
            disassembly = self.disassemble(self.pc)
            self.trace_file.write(f"{status}{flags} | {disassembly}\n")

        if command in self.commands:
            f = self.commands[command]["f"]
            m = self.commands[command]["m"]
            
            cycles = self.cycles.get(command, 2)
            
            if m in [Mode.ABSOLUTEX, Mode.ABSOLUTEY, Mode.INDIRECTY] and self.page_boundary_crossed(m):
                cycles += 1
            
            self.cycles_remaining = cycles
            
            f(m)
            self.pc += self.increments.get(m, 1)
            self.total_cycles += cycles
        else:
            print(f"ERROR: Opcode {command:02X} not implemented at location ${self.pc:04X}")
            self.debug_prompt()


    def get_location_by_mode(self,mode):
        if mode == Mode.IMMEDIATE:
            loc = self.pc + 1

        elif mode == Mode.ABSOLUTE:
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            loc = msb * 256 + lsb

        elif mode == Mode.ABSOLUTEX:
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            loc = msb * 256 + lsb
            loc += self.x

        elif mode == Mode.ABSOLUTEY:
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            loc = msb * 256 + lsb
            loc += self.y
        elif mode == Mode.ZEROPAGE:
            lsb = self.bus.read(self.pc + 1)

            loc = lsb

        elif mode == Mode.ZEROPAGEX:
            lsb = self.bus.read(self.pc + 1)
            loc = lsb + self.x
        
        elif mode == Mode.ZEROPAGEY:
            lsb = self.bus.read(self.pc + 1)
            loc = lsb + self.y

        
        elif mode == Mode.INDIRECT:
            # Get memory location where the JMP address os
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            loc = msb * 256 + lsb

            # Get the JMP address from memory location
            lsb = self.bus.read(loc)
            msb = self.bus.read(loc + 1)
            loc = msb * 256 + lsb
        
        elif mode == Mode.RELATIVE:
            loc = self.pc +1 
        
        elif mode == Mode.INDIRECTX:
            addr = self.bus.read(self.pc + 1)
            addr = (addr + self.x) & 0xFF
            lsb = self.bus.read(addr)
            msb = self.bus.read((addr + 1) & 0xFF)
            loc = (msb << 8) | lsb

        elif mode == Mode.INDIRECTY:
            addr = self.bus.read(self.pc + 1)
            lsb = self.bus.read(addr)
            msb = self.bus.read((addr + 1) & 0xFF)
            base_loc = (msb << 8) | lsb
            loc = base_loc + self.y

        return loc

    def page_boundary_crossed(self, mode):
        if mode == Mode.ABSOLUTEX:
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            address = (msb << 8) | lsb
            return (address & 0xFF00) != ((address + self.x) & 0xFF00)
        elif mode == Mode.ABSOLUTEY:
            lsb = self.bus.read(self.pc + 1)
            msb = self.bus.read(self.pc + 2)
            address = (msb << 8) | lsb
            return (address & 0xFF00) != ((address + self.y) & 0xFF00)
        elif mode == Mode.INDIRECTY:
            addr = self.bus.read(self.pc + 1)
            lsb = self.bus.read(addr)
            msb = self.bus.read((addr + 1) & 0xFF)
            base_loc = (msb << 8) | lsb
            return (base_loc & 0xFF00) != ((base_loc + self.y) & 0xFF00)
        return False
    
    def irq(self):
        self.irq_pending = True

    def nmi(self):
        self.nmi_pending = True

    def handle_irq(self):
        # Push PC to stack
        self.bus.write(0x0100 + self.sp, (self.pc >> 8) & 0xFF)
        self.sp -= 1
        self.bus.write(0x0100 + self.sp, self.pc & 0xFF)
        self.sp -= 1

        # Push status register to stack, with B flag cleared
        self.b = False
        self.PHP(Mode.IMPLIED)

        # Set interrupt disable flag
        self.i = True

        # Load PC from IRQ vector
        lsb = self.bus.read(0xFFFE)
        msb = self.bus.read(0xFFFF)
        self.pc = (msb << 8) | lsb
        
        self.irq_pending = False

    def handle_nmi(self):
        # Push PC to stack
        self.bus.write(0x0100 + self.sp, (self.pc >> 8) & 0xFF)
        self.sp -= 1
        self.bus.write(0x0100 + self.sp, self.pc & 0xFF)
        self.sp -= 1

        # Push status register to stack, with B flag cleared
        self.b = False
        self.PHP(Mode.IMPLIED)

        # Set interrupt disable flag
        self.i = True

        # Load PC from NMI vector
        lsb = self.bus.read(0xFFFA)
        msb = self.bus.read(0xFFFB)
        self.pc = (msb << 8) | lsb

        self.nmi_pending = False

    def BRK(self, mode):
        # Before handling the break, check if it's a KERNAL call we want to trap
        # This is a common pattern for trapping KERNAL calls.
        # For now, we only trap LOAD.
        if self.pc + 1 == 0xFFD5:
            if self.handle_kernal_load():
                # If handled, we effectively skip the BRK and the JSR that would follow
                self.pc += 2 # Skip the JSR instruction
                return

        self.pc += 1
        self.i = True
        self.handle_irq() # BRK uses the IRQ handler logic
        self.b = True

    def RTI(self, mode):
        self.PLP(mode)
        self.RTS(mode)
    # wrap 8 bit  value
    def wrap(self,value):
        if value > 255:
            value = value % 256
        elif value < 0:
            value += 256
        return value

    def set_nz(self, value):
        self.z = (value == 0)
        self.n = bool(value & 0x80)

    def BIT(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        result = self.a & value

        self.z = (result == 0)
        self.n = bool(value & 0x80)
        self.v = bool(value & 0x40)

    # LDA
    def LDA(self,mode):
        # Find the location based on the mode
        loc = self.get_location_by_mode(mode)
        # Load value from memory
        val = self.bus.read(loc)
        # Put that value in the accumulator
        self.a = val

        # Set nz
        self.set_nz(self.a)




    # LDX
    def LDX(self,mode):
        loc = self.get_location_by_mode(mode)
        # Load value from memory
        val = self.bus.read(loc)
        # Put that value in the accumulator
        self.x = val

        # Set nz
        self.set_nz(self.x)        


    # LDY
    def LDY(self,mode):
        loc = self.get_location_by_mode(mode)
        # Load value from memory
        val = self.bus.read(loc)
        # Put that value in the accumulator
        self.y = val

        # Set nz
        self.set_nz(self.y)        

    
    # STA - Absolute
    def STA(self,mode):
        # Find the location based on the mode
        loc = self.get_location_by_mode(mode)
        # Update memory
        self.bus.write(loc, self.a)

    # STX - Absolute
    def STX(self,mode):
        # Find the location based on the mode
        loc = self.get_location_by_mode(mode)
        # Update memory
        self.bus.write(loc, self.x)

    # STY - Absolute
    def STY(self,mode):
        # Find the location based on the mode
        loc = self.get_location_by_mode(mode)
        # Update memory
        self.bus.write(loc, self.y)
    
    def INC(self,mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        
        value += 1
        value = self.wrap(value)        
        self.bus.write(loc, value)
        # Set nz
        self.set_nz(value)        

    # Undocumented Opcodes
    # SLO (ASL + ORA)
    def SLO(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        self.c = bool(value & 0x80)
        value = (value << 1) & 0xFF
        self.bus.write(loc, value)
        self.a |= value
        self.set_nz(self.a)

    # RLA (ROL + AND)
    def RLA(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        carry_in = 1 if self.c else 0
        self.c = bool(value & 0x80)
        value = ((value << 1) | carry_in) & 0xFF
        self.bus.write(loc, value)
        self.a &= value
        self.set_nz(self.a)

    # SAX (Store A & X)
    def SAX(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.a & self.x
        self.bus.write(loc, value)

    # LAX (LDA + LDX)
    def LAX(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        self.a = value
        self.x = value
        self.set_nz(value)

    # DCP (DEC + CMP)
    def DCP(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        value = (value - 1) & 0xFF
        self.bus.write(loc, value)
        result = self.a - value
        self.c = (self.a >= value)
        self.set_nz(result)







    def INX(self,mode):
        self.x += 1
        self.x = self.wrap(self.x)
        # Set nz
        self.set_nz(self.x)        


    def INY(self,mode):
        self.y += 1
        self.y = self.wrap(self.y)
        # Set nz
        self.set_nz(self.y)        


    def DEC(self,mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        
        value -= 1
        value = self.wrap(value)        
        self.bus.write(loc, value)
        # Set nz
        self.set_nz(value)

    def DEX(self,mode):
        self.x -= 1
        self.x = self.wrap(self.x)
        # Set nz
        self.set_nz(self.x)        


    def DEY(self,mode):
        self.y -= 1
        self.y = self.wrap(self.y)
        # Set nz
        self.set_nz(self.y)        


    def TAX(self,mode):
        self.x = self.a
        # Set nz
        self.set_nz(self.a)        


    def TXA(self,mode):
        self.a = self.x
        # Set nz
        self.set_nz(self.a)        


    def TAY(self,mode):
        self.y = self.a
        # Set nz
        self.set_nz(self.y)        


    def TYA(self,mode):
        self.a = self.y
        # Set nz
        self.set_nz(self.a)        


    def CLC(self,mode):
        self.c = False

    def SEC(self,mode):
        self.c = True
    
    def CLI(self,mode):
        self.i = False

    def SEI(self,mode):
        self.i = True

    def CLV(self,mode):
        self.v = False

    def CLD(self,mode):
        self.d = False

    def SED(self,mode):
        self.d = True

    def JMP(self,mode):
        loc = self.get_location_by_mode(mode)
        self.pc = loc - self.increments[mode]

    def CMP(self,mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)

        result = self.a - value
        self.c = (self.a >= value)
        self.set_nz(result)

    def _compare(self, mode, register_value):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        result = register_value - value

        self.c = (register_value >= value)
        self.set_nz(result)

    # CPX
    def CPX(self, mode):
        self._compare(mode, self.x)

    # CPY
    def CPY(self, mode):
        self._compare(mode, self.y)

    def _branch(self, condition):
        if condition:
            # Branch is taken, add one cycle
            self.cycles_remaining += 1

            loc = self.get_location_by_mode(Mode.RELATIVE)
            value = self.bus.read(loc)

            # Recalculate if negative
            if value >= 128:
                value -= 256

            # The new PC will be the current PC + the relative offset.
            # The current PC has already been incremented by 2 in the tick method.
            new_pc = self.pc + value

            # If the page changes, add another cycle
            if (self.pc & 0xFF00) != (new_pc & 0xFF00):
                self.cycles_remaining += 1

            self.pc += value

    # BMI
    def BMI(self, mode):
        self._branch(self.n)

    # BPL
    def BPL(self, mode):
        self._branch(not self.n)
    
    # BVC
    def BVC(self, mode):
        self._branch(self.v)
    
    # BVS
    def BVS(self, mode):
        self._branch(not self.v)

    # BCC
    def BCC(self, mode):
        self._branch(not self.c)

    # BCS
    def BCS(self, mode):
        self._branch(self.c)

    # BNE
    def BNE(self, mode):
        self._branch(not self.z)

    # BEQ
    def BEQ(self, mode):
        self._branch(self.z)

    # TXS
    def TXS(self, mode):
        self.sp = self.x

    # TSX
    def TSX(self, mode):
        self.x = self.sp
        # Set nz
        self.set_nz(self.x)        


    # PHA
    def PHA(self, mode):
        # Find the location
        loc = 0x0100 + self.sp
        # Copy to the accumulator
        self.bus.write(loc, self.a)
        # Decrement the stack pointer
        self.sp -= 1
        # wrap
        self.sp = self.wrap(self.sp)


    # PLA
    def PLA(self, mode):
        self.sp += 1

        # Wrap
        self.sp = self.wrap(self.sp)

        #Find the location
        loc = 0x100 + self.sp

        # Copy the value to accumulator
        self.a = self.bus.read(loc)
        # Set nz
        self.set_nz(self.a)



    # PHP
    def PHP(self, mode):
        # nvb1dizc
        val = 0
        if self.n == True:
            val += 128
        if self.v == True:
            val += 64
        if self.b == True:
            val += 32
        val += 16
        if self.d == True:
            val += 8
        if self.i == True:
            val += 4
        if self.z == True:
            val += 2
        if self.c == True:
            val += 1

        # Find the location
        loc = 0x0100 + self.sp

        # Copy to the accumulator
        self.bus.write(loc, val)
        # Decrement the stack pointer
        self.sp -= 1
        # wrap
        self.sp = self.wrap(self.sp)

    # PLP
    def PLP(self, mode):
        self.sp += 1

        # Wrap
        self.sp = self.wrap(self.sp)

        #Find the location
        loc = 0x100 + self.sp

        # Copy the value to accumulator
        val = self.bus.read(loc)

        # Decode value and update flags
        if val & 128 == 128:
            self.n = True
        else:
            self.n = False

        if val & 64 == 64:
            self.v = True
        else:
            self.v = False

        if val & 32 == 32:
            self.b = True
        else:
            self.b = False

        
        if val & 8 == 8:
            self.d = True
        else:
            self.d = False

        if val & 4 == 4:
            self.i = True
        else:
            self.i = False
        
        if val & 2 == 2:
            self.z = True
        else:
            self.z = False

        if val & 1 == 1:
            self.c = True
        else:
            self.c = False


    # JSR
    def JSR(self, mode):
        # Return location (-1)
        loc = self.pc + 2
        
        # Push high byte of return address
        self.bus.write(0x0100 + self.sp, (loc >> 8) & 0xFF)
        self.sp -= 1
        self.sp = self.wrap(self.sp)

        # Push low byte of return address
        self.bus.write(0x0100 + self.sp, loc & 0xFF)
        self.sp -= 1
        self.sp = self.wrap(self.sp)
        
        # Change program counter to new location
        loc = self.get_location_by_mode(mode)
        self.pc = loc - self.increments[mode]




    # RTS
    def RTS(self, mode):
        # Copy A value to temp
        temp_a = self.a
        # Pull the lsb
        self.PLA(mode)
        lsb = self.a
        # Pull the msb
        self.PLA(mode)  
        msb = self.a


        # Restore temp to A
        self.a = temp_a

        # Set PC to return address
        loc = msb * 256 + lsb
        self.pc = loc

    
    # ADC
    def ADC(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)

        if self.d:
            # Decimal mode
            carry = 1 if self.c else 0
            
            # Add lower nibbles
            low = (self.a & 0x0F) + (value & 0x0F) + carry
            if low > 9:
                low += 6

            # Add upper nibbles
            high = (self.a >> 4) + (value >> 4)
            if low > 0x0F:
                high += 1
            
            # N and V flags are not valid in decimal mode on NMOS 6502
            # We can leave them as they are or update based on binary result before correction

            if high > 9:
                high += 6

            self.c = high > 0x0F
            self.a = ((high & 0x0F) << 4) | (low & 0x0F)
            self.set_nz(self.a)

        else:
            # Binary mode
            # Add value to the accumulator
            result = self.a + value + (1 if self.c else 0)

            # Set V flag
            self.v = bool((~(self.a ^ value) & (self.a ^ result)) & 0x80)

            # Carry and wrap around
            self.c = result > 0xFF
            self.a = self.wrap(result)
            
            # Set nz
            self.set_nz(self.a)


    # SBC
    def SBC(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)
        
        if self.d:
            # Decimal mode
            borrow = 0 if self.c else 1
            
            # Subtract lower nibbles
            low = (self.a & 0x0F) - (value & 0x0F) - borrow
            if low < 0:
                low -= 6

            # Subtract upper nibbles
            high = (self.a >> 4) - (value >> 4)
            if low < 0:
                high -= 1
            
            if high < 0:
                high -= 6

            self.c = high >= 0
            self.a = ((high & 0x0F) << 4) | (low & 0x0F)
            self.set_nz(self.a)
        else:
            # Binary mode
            result = self.a - value - (0 if self.c else 1)

            # Set V flag
            self.v = bool(((self.a ^ value) & (self.a ^ result)) & 0x80)

            self.c = result >= 0
            self.a = self.wrap(result)
            
            self.set_nz(self.a)



    # AND
    def AND(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)

        # Perform logical AND
        self.a = self.a & value

        # Set nz
        self.set_nz(self.a)

    # ORA
    def ORA(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)

        # Perform logical ORA
        self.a = self.a | value

        # Set nz
        self.set_nz(self.a)        


    # EOR
    def EOR(self, mode):
        loc = self.get_location_by_mode(mode)
        value = self.bus.read(loc)

        # Perform logical EOR
        self.a = self.a ^ value
        
        # Set nz
        self.set_nz(self.a)        


    # NOP
    def NOP(self, mode):
        pass

    # ASL
    def ASL(self, mode):
        if mode == Mode.ACCUMULATOR:
            value = self.a
        else:
            loc = self.get_location_by_mode(mode)
            value = self.bus.read(loc)
        
        # Check the leftmost bit
        if value & 128 == 128:
            self.c = True
        
        # Shift Left
        value = value << 1  # shift 1 bit to left
        value = self.wrap(value)


        # Put the value into the accumulator or memory
        if mode == Mode.ACCUMULATOR:
            self.a = value
        else:
            self.bus.write(loc, value)
        
        # Set nz
        self.set_nz(value)


    # LSR
    def LSR(self, mode):
        if mode == Mode.ACCUMULATOR:
            value = self.a
        else:
            loc = self.get_location_by_mode(mode)
            value = self.bus.read(loc)
        
        # Check the rightmost bit
        if value & 1 == 1:
            self.c = True
        
        # Shift Right
        value = value >> 1  # shift 1 bit to rigth
        value = self.wrap(value)


        # Put the value into the accumulator or memory
        if mode == Mode.ACCUMULATOR:
            self.a = value
        else:
            self.bus.write(loc, value)
        
        # Set nz
        self.set_nz(value)        

        
    # ROL
    def ROL(self, mode):
        if mode == Mode.ACCUMULATOR:
            value = self.a
        else:
            loc = self.get_location_by_mode(mode)
            value = self.bus.read(loc)
        
        # Check carry bit
        temp = 0
        if self.c == True:
            temp = 1
        
        # Check the leftmost bit
        if value & 128 == 128:
            self.c = True
        else:
            self.c = False  
        
        # Shift Left
        value = value << 1  # shift 1 bit to left
        value = self.wrap(value)

        # Add the carry
        value = value | temp


        # Put the value into the accumulator or memory
        if mode == Mode.ACCUMULATOR:
            self.a = value
        else:
            self.bus.write(loc, value)
        
        # Set nz
        self.set_nz(value)        


    # ROR
    def ROR(self, mode):
        if mode == Mode.ACCUMULATOR:
            value = self.a
        else:
            loc = self.get_location_by_mode(mode)
            value = self.bus.read(loc)
        
        # Check carry bit
        temp = 0
        if self.c == True:
            temp = 128
        
        # Check the rightmost bit
        if value & 1 == 1:
            self.c = True
        else:
            self.c = False  
        
        # Shift Right
        value = value >> 1  # shift 1 bit to right
        value = self.wrap(value)

        # Add the carry
        value = value | temp


        # Put the value into the accumulator or memory
        if mode == Mode.ACCUMULATOR:
            self.a = value
        else:
            self.bus.write(loc, value)
        
        # Set nz
        self.set_nz(value)        

 



    # Testing /Debugging
    def push(self, value):        
        self.bus.write(self.pc, value)
        self.pc += 1
    
    def disassemble(self, addr):
        """Disassembles a single instruction at a given address."""
        opcode = self.bus.read(addr)
        
        if opcode not in self.commands:
            return f"${addr:04X}: {opcode:02X}       ???"

        mnemonic = self.commands[opcode]['f'].__name__
        mode = self.commands[opcode]['m']
        
        operand_str = ""
        if mode == Mode.IMMEDIATE:
            operand_str = f"#${self.bus.read(addr + 1):02X}"
        elif mode == Mode.ZEROPAGE:
            operand_str = f"${self.bus.read(addr + 1):02X}"
        elif mode == Mode.ZEROPAGEX:
            operand_str = f"${self.bus.read(addr + 1):02X},X"
        elif mode == Mode.ZEROPAGEY:
            operand_str = f"${self.bus.read(addr + 1):02X},Y"
        elif mode == Mode.ABSOLUTE:
            lsb = self.bus.read(addr + 1)
            msb = self.bus.read(addr + 2)
            operand_str = f"${(msb << 8) | lsb:04X}"
        elif mode == Mode.ABSOLUTEX:
            lsb = self.bus.read(addr + 1)
            msb = self.bus.read(addr + 2)
            operand_str = f"${(msb << 8) | lsb:04X},X"
        elif mode == Mode.ABSOLUTEY:
            lsb = self.bus.read(addr + 1)
            msb = self.bus.read(addr + 2)
            operand_str = f"${(msb << 8) | lsb:04X},Y"
        elif mode == Mode.INDIRECT:
            lsb = self.bus.read(addr + 1)
            msb = self.bus.read(addr + 2)
            operand_str = f"(${(msb << 8) | lsb:04X})"
        elif mode == Mode.INDIRECTX:
            operand_str = f"(${self.bus.read(addr + 1):02X},X)"
        elif mode == Mode.INDIRECTY:
            operand_str = f"(${self.bus.read(addr + 1):02X}),Y"
        elif mode == Mode.RELATIVE:
            offset = self.bus.read(addr + 1)
            if offset >= 128: offset -= 256
            target = addr + 2 + offset
            operand_str = f"${target:04X}"

        return f"${addr:04X}: {mnemonic} {operand_str}"

    def _display_memory(self, start_addr, length=32):
        """Displays a block of memory in hex and ASCII format."""
        print(f"--- Memory View from ${start_addr:04X} ---")
        for i in range(0, length, 16):
            current_addr = start_addr + i
            if current_addr > 0xFFFF:
                break
            
            # Read 16 bytes or fewer if near end of memory
            bytes_to_read = min(16, 0x10000 - current_addr)
            if bytes_to_read <= 0:
                break

            data_hex = []
            data_ascii = []
            for j in range(bytes_to_read):
                byte = self.bus.read(current_addr + j)
                data_hex.append(f"{byte:02X}")
                data_ascii.append(chr(byte) if 0x20 <= byte <= 0x7E else '.')
            
            print(f"${current_addr:04X}: {' '.join(data_hex).ljust(48)} | {''.join(data_ascii)}")
        print("--------------------------")

    def _search_memory(self, sequence):
        """Searches for a byte sequence in memory and prints found addresses."""
        if not sequence:
            print("Search sequence cannot be empty.")
            return

        sequence_str = ' '.join(f'{b:02X}' for b in sequence)
        print(f"Searching for sequence: {sequence_str}...")

        found_addresses = []
        seq_len = len(sequence)
        for addr in range(0x10000 - seq_len + 1):
            match = True
            for i in range(seq_len):
                if self.bus.read(addr + i) != sequence[i]:
                    match = False
                    break
            if match:
                found_addresses.append(addr)

        if found_addresses:
            print(f"Found {len(found_addresses)} match(es) at:")
            print(' '.join(f'${addr:04X}' for addr in found_addresses))
        else:
            print("Sequence not found.")

    def _set_register(self, register, value):
        """Sets the value of a CPU register."""
        try:
            value = int(value, 16)
        except ValueError:
            print(f"Invalid value: {value}")
            return

        if register == "a":
            self.a = value & 0xFF
        elif register == "x":
            self.x = value & 0xFF
        elif register == "y":
            self.y = value & 0xFF
        elif register == "pc":
            self.pc = value & 0xFFFF
        elif register == "sp":
            self.sp = value & 0xFF
        else:
            print(f"Invalid register: {register}")
            return

        print(f"Set {register.upper()} to ${value:02X}")

    def _disassemble_range(self, start_addr, num_instructions=10):
        """Disassembles a range of instructions."""
        print(f"--- Disassembly from ${start_addr:04X} ---")
        addr = start_addr
        for _ in range(num_instructions):
            if addr > 0xFFFF:
                break
            
            disassembly_line = self.disassemble(addr)
            print(disassembly_line)
            
            opcode = self.bus.read(addr)
            if opcode in self.commands:
                mode = self.commands[opcode]['m']
                addr += self.increments.get(mode, 1)
            else:
                addr += 1 # If opcode is unknown, just advance by one byte
        print("-----------------------------")

    def _backtrace(self):
        """Shows a simulated call stack by unwinding JSR return addresses."""
        print("--- Call Stack (Backtrace) ---")
        # The 6502 stack grows downwards from 0x01FF. SP points to the next free slot.
        # The current stack contents are from SP+1 to 0xFF.
        current_sp = self.sp
        frame_count = 0

        # Print the current location as frame #0
        print(f"  #{frame_count}: {self.disassemble(self.pc)}")
        frame_count += 1

        # Unwind the stack, looking for JSR return addresses
        while current_sp < 0xFF:
            # A JSR pushes a 2-byte return address (PC+2). RTS pulls it and jumps to (addr+1).
            # So, the address on the stack points to the last byte of the JSR instruction.
            lsb = self.bus.read(0x0100 + current_sp + 1)
            msb = self.bus.read(0x0100 + current_sp + 2)
            return_addr = (msb << 8) | lsb
            print(f"  #{frame_count}: (JSR from ${return_addr - 2:04X}) -> returns to ${return_addr + 1:04X}")
            current_sp += 2
            frame_count += 1
        print("------------------------------")

    def _save_state(self, filename):
        """Saves the current emulator state to a file."""
        state = {
            'cpu': {
                'a': self.a, 'x': self.x, 'y': self.y,
                'pc': self.pc, 'sp': self.sp,
                'n': self.n, 'v': self.v, 'b': self.b,
                'd': self.d, 'i': self.i, 'z': self.z, 'c': self.c,
                'total_cycles': self.total_cycles,
            },
            'ram': self.bus.memory.ram,
            'vic': self.bus.vic.save_state(),
            'sid': self.bus.sid.save_state(),
            'cia1': self.bus.cia1.save_state(),
            'cia2': self.bus.cia2.save_state()
        }
        try:
            with open(filename, 'w') as f:
                json.dump(state, f, indent=4)
            print(f"Emulator state saved to '{filename}'.")
            # Add a small visual confirmation in the GUI title
            if 'pygame' in sys.modules:
                pygame.display.set_caption("pyC64emu - State Saved!")

        except IOError as e:
            print(f"Error saving state: {e}")

    def _capture_state_for_rewind(self):
        """Captures the current emulator state into a dictionary for rewinding."""
        # This is similar to _save_state but returns the dictionary directly
        # without writing to a file.
        state = {
            'cpu': {
                'a': self.a, 'x': self.x, 'y': self.y,
                'pc': self.pc, 'sp': self.sp,
                'n': self.n, 'v': self.v, 'b': self.b,
                'd': self.d, 'i': self.i, 'z': self.z, 'c': self.c,
                'total_cycles': self.total_cycles,
            },
            # Store only the *changes* in RAM since the last capture
            'ram_changes': {addr: self.bus.memory.ram[addr] for addr in self.bus.memory_dirty_flags},
            # Clear the dirty flags *after* capturing the changes
            'dirty_flags': list(self.bus.memory_dirty_flags),
            'vic': self.bus.vic.save_state(),
            'sid': self.bus.sid.save_state(),
            'cia1': self.bus.cia1.save_state(),
            'cia2': self.bus.cia2.save_state()
        }
        return state

    def _restore_state(self, filename):
        """Restores the emulator state from a file."""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            cpu_state = state['cpu']
            self.a = cpu_state['a']
            self.x = cpu_state['x']
            self.y = cpu_state['y']


            self.pc = cpu_state['pc']
            self.sp = cpu_state['sp']
            self.n = cpu_state['n']
            self.v = cpu_state['v']
            self.b = cpu_state['b']
            self.d = cpu_state['d']
            self.i = cpu_state['i']
            self.z = cpu_state['z']
            self.c = cpu_state['c']
            self.total_cycles = cpu_state.get('total_cycles', 0) # Use .get for backward compatibility

            # Restore only the *changed* memory locations
            ram_changes = state.get('ram_changes', {})
            for addr, value in ram_changes.items():
                self.bus.memory.ram[addr] = value

            # Clear the dirty flags *after* restoring the RAM
            self.bus.memory_dirty_flags = set(state.get('dirty_flags', []))
            self.bus.vic.restore_state(state['vic'])
            self.bus.sid.restore_state(state['sid'])
            self.bus.cia1.restore_state(state['cia1'])
            self.bus.cia2.restore_state(state['cia2'])

            print(f"Emulator state restored from '{filename}'.")
            
            # Add a small visual confirmation in the GUI title
            if 'pygame' in sys.modules:
                pygame.display.set_caption("pyC64emu - State Loaded!")

            self.debug_prompt() # Re-enter debugger to show new state
        except FileNotFoundError:
            print(f"Error: State file '{filename}' not found.")
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Error restoring state: {e}")

    def _restore_state_from_dict(self, state):
        """Restores the emulator state from a dictionary (for rewind)."""
        try:
            cpu_state = state['cpu']
            self.a = cpu_state['a']
            self.x = cpu_state['x']
            self.y = cpu_state['y']
            self.pc = cpu_state['pc']
            self.sp = cpu_state['sp']
            self.n = cpu_state['n']
            self.v = cpu_state['v']
            self.b = cpu_state['b']
            self.d = cpu_state['d']
            self.i = cpu_state['i']
            self.z = cpu_state['z']
            self.c = cpu_state['c']
            self.total_cycles = cpu_state.get('total_cycles', 0)

            for addr, value in state.get('ram_changes', {}).items():
                self.bus.memory.ram[int(addr)] = value # JSON keys are strings

            self.bus.vic.restore_state(state['vic'])
            self.bus.sid.restore_state(state['sid'])
            self.bus.cia1.restore_state(state['cia1'])
            self.bus.cia2.restore_state(state['cia2'])
        except KeyError as e:
            print(f"Error restoring state from dictionary: Missing key {e}")

    def handle_kernal_load(self):
        """High-level emulation of the KERNAL LOAD routine."""
        # Check if a disk is attached
        if not self.bus.drive or not self.bus.drive.disk_image:
            return False # Let the real KERNAL handle it (it will time out)

        # Get filename length from $B8
        filename_len = self.bus.read(0xB8)
        # Get filename address from $BB/$BC
        filename_addr = self.bus.read(0xBB) | (self.bus.read(0xBC) << 8)

        # Read filename from memory
        filename_bytes = [self.bus.read(filename_addr + i) for i in range(filename_len)]
        filename = bytes(filename_bytes).decode('petscii-c64en-lc', errors='ignore')

        print(f"HLE: Intercepted KERNAL LOAD for file '{filename}'")

        # Load the file using the drive
        file_data = self.bus.drive.load_file(filename)

        if file_data:
            # First two bytes of PRG data are the load address
            load_addr = file_data[0] | (file_data[1] << 8)
            program_data = file_data[2:]
            
            # Write program data to RAM
            for i, byte in enumerate(program_data):
                self.bus.write(load_addr + i, byte)
            
            print(f"HLE: Loaded {len(program_data)} bytes to ${load_addr:04X}")
            self.c = False # Set Carry to indicate success
            self.pc += 2 # Simulate RTS by advancing PC past the JSR instruction
            return True
        else:
            print(f"HLE: File '{filename}' not found.")
            self.c = True # Set Carry to indicate error
            self.pc += 2
            return True

    def handle_kernal_save(self):
        """High-level emulation of the KERNAL SAVE routine."""
        if not self.bus.drive or not self.bus.drive.disk_image:
            return False

        # Get filename length from $B8
        filename_len = self.bus.read(0xB8)
        # Get filename address from $BB/$BC
        filename_addr = self.bus.read(0xBB) | (self.bus.read(0xBC) << 8)

        # Read filename from memory
        filename_bytes = [self.bus.read(filename_addr + i) for i in range(filename_len)]
        filename = bytes(filename_bytes).decode('petscii-c64en-lc', errors='ignore')

        # For SAVE, the start address is in A (lsb) and X (msb) on entry.
        # However, BASIC sets up pointers in zero page. Let's use those.
        # Start of BASIC program is $0801. End is pointed to by $2D/$2E.
        start_addr = self.bus.read(0x2B) | (self.bus.read(0x2C) << 8)
        end_addr = self.bus.read(0x2D) | (self.bus.read(0x2E) << 8)

        print(f"HLE: Intercepted KERNAL SAVE for file '{filename}'")
        print(f"HLE: Saving memory from ${start_addr:04X} to ${end_addr:04X}")

        # Prepare data to save (including the 2-byte load address header)
        data_to_save = bytearray([start_addr & 0xFF, start_addr >> 8])
        data_to_save.extend([self.bus.read(i) for i in range(start_addr, end_addr)])

        if self.bus.drive.save_file(filename, data_to_save):
            self.c = False # Success
        else:
            self.c = True # Error
        self.pc += 2 # Simulate RTS
        return True

    def debug_prompt(self):
        """Enters the interactive debugger."""
        print("--- DEBUGGER ---")
        status = f"A:{self.a:02X} X:{self.x:02X} Y:{self.y:02X} PC:{self.pc:04X} SP:{self.sp:02X}"
        flags = f"  Flags: {'N' if self.n else '-'} {'V' if self.v else '-'} {'B' if self.b else '-'} {'D' if self.d else '-'} {'I' if self.i else '-'} {'Z' if self.z else '-'} {'C' if self.c else '-'}"
        print(status + flags)
        
        if self.auto_dasm_on_break:
            self._disassemble_range(self.pc, 5)
        else:
            print(f"Next -> {self.disassemble(self.pc)}")
        
        while True:
            command = input("> ").strip()
            if command == "" or command == "s" or command == "step":
                break
            elif command.startswith("b "):
                parts = command.split()
                if len(parts) > 1 and parts[1] == "clear":
                    if len(parts) > 2 and parts[2] == "all":
                        self.breakpoints.clear()
                        print("All breakpoints cleared.")
                    elif len(parts) > 2:
                        try:
                            addr_to_clear = int(parts[2], 16)
                            if addr_to_clear in self.breakpoints:
                                self.breakpoints.remove(addr_to_clear)
                                print(f"Breakpoint at ${addr_to_clear:04X} cleared.")
                            else:
                                print(f"No breakpoint found at ${addr_to_clear:04X}.")
                        except ValueError:
                            print("Invalid address for 'b clear'.")
                    else:
                        print("Usage: 'b clear <addr>' or 'b clear all'.")
                elif len(parts) == 2:
                    try:
                        addr = int(parts[1], 16)
                        self.breakpoints.add(addr)
                        print(f"Breakpoint set at ${addr:04X}")
                    except (ValueError, IndexError):
                        print("Invalid address.")

            elif command.startswith("m "):
                try:
                    parts = command.split(" ")
                    start_addr = int(parts[1], 16)
                    length = int(parts[2]) if len(parts) > 2 else 32
                    self._display_memory(start_addr, length)
                except (ValueError, IndexError):
                    print("Invalid memory command. Use 'm <address> [length]' (e.g., 'm 0200 64').")
            elif command.startswith("set "):
                try:
                    parts = command.split(" ")
                    address = int(parts[1], 16)
                    value = int(parts[2], 16)
                    self.bus.write(address, value)
                    print(f"Set memory at ${address:04X} to ${value:02X}")
                except (ValueError, IndexError):
                    print("Invalid set command. Use 'set <address> <value>' (e.g., 'set 8000 0A').")
            elif command.startswith("search ") or command.startswith("find "):
                try:
                    parts = command.split(" ")[1:]
                    if not parts:
                        raise ValueError
                    byte_sequence = [int(p, 16) for p in parts]
                    self._search_memory(byte_sequence)
                except (ValueError, IndexError):
                    print("Invalid search command. Use 'search <byte1> <byte2> ...' (e.g., 'search A9 10 AA').")
            elif command.startswith("reg "):
                try:
                    parts = command.split(" ")
                    register = parts[1].lower()
                    value = parts[2]
                    self._set_register(register, value)
                except (ValueError, IndexError):
                    print("Invalid reg command. Use 'reg <register> <value>' (e.g., 'reg a 0A').")

            elif command.startswith("dasm "):
                try:
                    parts = command.split(" ")
                    start_addr = int(parts[1], 16)
                    num_instructions = int(parts[2]) if len(parts) > 2 else 10
                    self._disassemble_range(start_addr, num_instructions)
                except (ValueError, IndexError):
                    print("Invalid disassemble command. Use 'dasm <address> [num_instructions]' (e.g., 'dasm 8000 5').")
            elif command == "autodasm":
                self.auto_dasm_on_break = not self.auto_dasm_on_break
                if self.auto_dasm_on_break:
                    print("Auto-disassembly on break is now ON.")
                else:
                    print("Auto-disassembly on break is now OFF.")

            elif command == "trace":
                if not self.tracing:
                    try:
                        self.trace_file = open("trace.log", "w")
                        self.tracing = True
                        print("Tracing started. Output will be written to trace.log. Use 'c' to run.")
                    except IOError:
                        print("Error: Could not open trace.log for writing.")
                else:
                    self.tracing = False
                    if self.trace_file:
                        self.trace_file.close()
                        self.trace_file = None
                    print("Tracing stopped.")

            elif command == "flags":
                print("--- CPU Flags ---")
                print(f"  N (Negative) : {int(self.n)}")
                print(f"  V (Overflow) : {int(self.v)}")
                print(f"  - (Unused)   : 1")
                print(f"  B (Break)    : {int(self.b)}")
                print(f"  D (Decimal)  : {int(self.d)}")
                print(f"  I (Interrupt): {int(self.i)}")
                print(f"  Z (Zero)     : {int(self.z)}")
                print(f"  C (Carry)    : {int(self.c)}")
                print("-----------------")

            elif command == "breakpoints" or command == "blist":
                if not self.breakpoints:
                    print("No active breakpoints.")
                else:
                    print("Active breakpoints:")
                    sorted_bps = sorted(list(self.breakpoints))
                    print(' '.join(f'${addr:04X}' for addr in sorted_bps))

            elif command == "c" or command == "continue":
                break
            elif command == "stack":
                # The 6502 stack is on page 1 (0x0100 - 0x01FF) and grows downwards.
                # self.sp points to the next free byte.
                # The items currently on the stack are from sp+1 to 0xFF.
                stack_start = 0x0100 + self.sp + 1
                stack_size = 0xFF - self.sp
                print(f"--- Stack (SP is at ${0x0100 + self.sp:04X}) ---")
                if stack_size > 0:
                    self._display_memory(stack_start, stack_size)
            elif command == "h" or command == "help":
                print("Debugger commands:")
                print("  s (step)        - Execute current instruction and break on next.")
                print("  c (continue)    - Continue execution until next breakpoint.")
                print("  b <addr>        - Set a breakpoint (e.g., b 8000).")
                print("  b clear <addr>  - Clear a specific breakpoint.")
                print("  b clear all     - Clear all breakpoints.")
                print("  blist           - List all active breakpoints.")
                print("  m <addr> [len]  - Display memory from hex address (e.g., m 0200 32).")
                print("  save [filename] - Save emulator state (default: emustate.json).")
                print("  load [filename] - Restore emulator state (default: emustate.json).")
                print("  h (help)        - Show this help message.")
                print("  dasm <addr> [n] - Disassemble n instructions from address (e.g., dasm 8000 5).")
                print("  find <b1> [b2]..- Search for a byte sequence in memory (e.g., find A9 20 85 30).")
                print("  autodasm        - Toggle automatic disassembly when a breakpoint is hit.")
                print("  reg <reg> <value> - Set CPU register to value (e.g., reg a 0A).")
                print("  set <addr> <value> - Set memory at hex address to hex value (e.g., set 8000 0A).")
                print("  flags           - Show a detailed view of the status flags.")
                print("  stack           - Display the current contents of the stack.")
                print("  bt              - Show a backtrace of the call stack.")
                print("  trace           - Toggle instruction tracing to trace.log.")
                print("  cycles          - Show the total cycle count.")
            elif command.startswith("save"):
                parts = command.split()
                filename = parts[1] if len(parts) > 1 else "emustate.json"
                self._save_state(filename)
            elif command.startswith("load") or command.startswith("restore"):
                parts = command.split()
                filename = parts[1] if len(parts) > 1 else "emustate.json"
                self._restore_state(filename)
                # After restoring, we break the loop to re-evaluate the new state
                break
            elif command == "bt" or command == "callstack":
                self._backtrace()


            else:
                print("Unknown command. Type 'h' or 'help' for a list of commands.")
        
        if command == "c" or command == "continue":
            # To continue, we need to remove the current breakpoint if we are on one
            if self.pc in self.breakpoints:
                self.breakpoints.remove(self.pc)
