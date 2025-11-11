# pyc64/memory.py

class MemoryManager:
    """
    Handles the C64 memory map, including RAM, ROMs, and bank switching.
    This class contains the core logic for how memory is accessed.
    """
    def __init__(self, bus):
        self.bus = bus
        # C64 has 64KB of RAM
        self.ram = [0x00] * 0x10000
        # ROMs
        self.basic_rom = [0x00] * 0x2000  # 8KB
        self.kernal_rom = [0x00] * 0x2000 # 8KB
        self.char_rom = [0x00] * 0x1000   # 4KB
        # Color RAM
        self.color_ram = [0x00] * 0x0400 # 1KB

        # Processor port at $0001, controls bank switching.
        self.processor_port = 0x37  # Default power-on state

    def read(self, address):
        # The processor port at $0000/$0001 has special behavior.
        # Reading $0000 returns the value of the port direction register.
        # Reading $0001 returns the latched value of the port.
        if address == 0x0000:
            # The direction register is fixed in the C64.
            return 0x2F # Default value for the 6510's port direction register
        if address == 0x0001:
            # The value written to $0001 updates the processor port, which controls bank switching.
            # The write also goes to the underlying RAM.
            return self.processor_port

        # Determine memory mapping based on processor port
        loram = (self.processor_port >> 0) & 1
        hiram = (self.processor_port >> 1) & 1
        charen = (self.processor_port >> 2) & 1

        # The C64 memory map is determined by the combination of these bits
        # and the address being accessed.
        # See: https://www.c64-wiki.com/wiki/Bank_Switching

        # $A000-$BFFF: BASIC ROM or RAM
        if 0xA000 <= address <= 0xBFFF:
            if loram and hiram:
                return self.basic_rom[address - 0xA000]

        # $D000-$DFFF: I/O, Character ROM, or RAM
        elif 0xD000 <= address <= 0xDFFF:
            # When charen is 0, Character ROM is visible.
            # When charen is 1, I/O is visible.
            # Both are only visible if either LORAM or HIRAM is also active.
            if loram or hiram:
                if charen: # I/O visible
                    if 0xD000 <= address <= 0xD3FF: return self.bus.vic.read(address)
                    if 0xD400 <= address <= 0xD7FF: return self.bus.sid.read(address)
                    if 0xD800 <= address <= 0xDBFF: return self.color_ram[address - 0xD800]
                    if 0xDC00 <= address <= 0xDCFF: return self.bus.cia1.read(address)
                    if 0xDD00 <= address <= 0xDDFF: return self.bus.cia2.read(address)
                else: # Character ROM visible
                    return self.char_rom[address - 0xD000]

        # $E000-$FFFF: KERNAL ROM or RAM
        elif 0xE000 <= address <= 0xFFFF:
            if hiram:
                return self.kernal_rom[address - 0xE000]

        # If no ROM or I/O was mapped at the given address, fall through to RAM.
        return self.ram[address]

    def write(self, address, data):
        # The processor port at $0001 is always writable to the RAM underneath.
        # Its value is also latched to control bank switching.
        if address == 0x0001:
            # The value written to $0001 updates the processor port, which controls bank switching.
            # The write also goes to the underlying RAM.
            self.ram[address] = data
            self.processor_port = data

        # Determine memory mapping based on processor port
        loram = (self.processor_port >> 0) & 1
        hiram = (self.processor_port >> 1) & 1
        charen = (self.processor_port >> 2) & 1

        # Writes to ROM areas are ignored if the ROM is banked in.
        # Otherwise, the write goes to the underlying RAM.

        # $A000-$BFFF: BASIC ROM or RAM
        if 0xA000 <= address <= 0xBFFF:
            if loram and hiram:
                return  # Write is ignored when BASIC ROM is visible

        # $D000-$DFFF: I/O, Character ROM, or RAM
        elif 0xD000 <= address <= 0xDFFF:
            if loram or hiram:
                if charen: # I/O visible
                    if 0xD000 <= address <= 0xD3FF: self.bus.vic.write(address, data); return
                    if 0xD400 <= address <= 0xD7FF: self.bus.sid.write(address, data); return
                    if 0xD800 <= address <= 0xDBFF: self.color_ram[address - 0xD800] = data; return
                    if 0xDC00 <= address <= 0xDCFF: self.bus.cia1.write(address, data); return
                    if 0xDD00 <= address <= 0xDDFF: self.bus.cia2.write(address, data); return
                else: # Character ROM visible
                    # Writes to Character ROM area go to underlying RAM, except for Color RAM
                    if 0xD800 <= address <= 0xDBFF:
                        self.color_ram[address - 0xD800] = data
                        return

        # $E000-$FFFF: KERNAL ROM or RAM
        elif 0xE000 <= address <= 0xFFFF:
            if hiram:
                return  # Write is ignored when KERNAL ROM is visible

        # Default to RAM write if no other area handled the write.
        self.ram[address] = data

    def load_rom(self, rom_type, data):
        if rom_type == 'basic':
            self.basic_rom[:len(data)] = data
        elif rom_type == 'kernal':
            self.kernal_rom[:len(data)] = data
        elif rom_type == 'char':
            self.char_rom[:len(data)] = data