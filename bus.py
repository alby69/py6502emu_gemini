# 6502 Bus
# By @TokyoEdtech

from vic2 import VICII
from sid import SID
from cia import CIA
from drive1541 import DiskDrive1541
import struct

class Cartridge:
    """Represents a C64 cartridge."""
    def __init__(self):
        self.type = 0
        self.exrom = False
        self.game = False
        self.rom_chips = {} # Maps address to ROM data list

    def load_from_crt(self, filename):
        """Parses a .crt file and loads its data."""
        with open(filename, 'rb') as f:
            # Read CRT header
            magic = f.read(16)
            if magic[:4] != b'C64 ':
                raise ValueError("Invalid CRT file magic string.")
            
            header_len = struct.unpack('>I', f.read(4))[0]
            self.type = struct.unpack('>H', f.read(2))[0]
            self.exrom = (struct.unpack('>B', f.read(1))[0] == 1)
            self.game = (struct.unpack('>B', f.read(1))[0] == 1)
            f.seek(header_len) # Move to the end of the header

            # Read CHIP packets
            while True:
                chip_header = f.read(16)
                if not chip_header or chip_header[:4] != b'CHIP':
                    break
                
                chip_size = struct.unpack('>I', chip_header[8:12])[0]
                load_addr = struct.unpack('>H', chip_header[14:16])[0]
                self.rom_chips[load_addr] = list(f.read(chip_size))
        print(f"Loaded Cartridge '{filename}', Type: {self.type}, GAME: {self.game}, EXROM: {self.exrom}")

class Bus:
    def __init__(self, cpu=None):
        # C64 has 64KB of RAM
        self.ram = [0x00] * 0x10000

        # ROMs
        self.basic_rom = [0x00] * 0x2000 # 8KB
        self.kernal_rom = [0x00] * 0x2000 # 8KB

        # Link to CPU for interrupts
        self.cpu = cpu

        # Processor port at $0001, controls bank switching. Default C64 config.
        self.processor_port = 0b00110111

        # Track memory writes for rewind
        self.memory_dirty_flags = set()

        # Cartridge
        self.cartridge = None

        # I/O Devices
        self.vic = VICII(self, cpu=self.cpu)
        self.sid = SID()
        self.cia1 = CIA("CIA1", is_cia1=True, cpu=self.cpu) # CIA1 handles keyboard
        self.cia2 = CIA("CIA2", cpu=self.cpu)

        # Disk Drive
        self.drive = DiskDrive1541()

    def write(self, address, data):
        if address == 0x0001:
            self.processor_port = data
            # Also write to RAM underneath the port
            self.ram[0x0001] = data
            return

        # Determine memory mapping based on processor port
        loram = (self.processor_port >> 0) & 1
        hiram = (self.processor_port >> 1) & 1
        charen = (self.processor_port >> 2) & 1

        # Cartridge logic overrides standard bank switching for $8000-$BFFF
        if self.cartridge:
            if self.cartridge.game and not self.cartridge.exrom:
                # Game line asserted, EXROM deasserted (e.g., Ultimax mode)
                if 0x8000 <= address <= 0x9FFF and 0x8000 in self.cartridge.rom_chips:
                    return # Write to cartridge ROM ignored
                if 0xE000 <= address <= 0xFFFF and 0xE000 in self.cartridge.rom_chips:
                    return # Write to cartridge ROM ignored

        # Standard memory map
        if 0xA000 <= address <= 0xBFFF:
            if self.cartridge and not self.cartridge.exrom and 0xA000 in self.cartridge.rom_chips:
                return # Write to 16k Cartridge ROM ignored
            if loram: return # Write to BASIC ROM ignored
        elif 0xD000 <= address <= 0xDFFF:
            if loram and hiram and charen:
                if 0xD000 <= address <= 0xD3FF: self.vic.write(address, data)
                elif 0xD400 <= address <= 0xD7FF: self.sid.write(address, data)
                elif 0xDC00 <= address <= 0xDCFF: self.cia1.write(address, data)
                elif 0xDD00 <= address <= 0xDDFF: self.cia2.write(address, data)
                elif 0xD800 <= address <= 0xDBFF: self.ram[address] = data
                return
        elif 0xE000 <= address <= 0xFFFF:
            if hiram: return # Write to KERNAL ROM ignored

        # Default to RAM write
        self.ram[address] = data
        # Add address to dirty flags for rewind
        self.memory_dirty_flags.add(address)

    def read(self, address):
        # Determine memory mapping based on processor port
        loram = (self.processor_port >> 0) & 1
        hiram = (self.processor_port >> 1) & 1
        charen = (self.processor_port >> 2) & 1

        # Cartridge logic can override standard bank switching
        if self.cartridge:
            # GAME=1, EXROM=0 (e.g., Ultimax mode)
            if self.cartridge.game and not self.cartridge.exrom:
                if 0x8000 <= address <= 0x9FFF and 0x8000 in self.cartridge.rom_chips:
                    return self.cartridge.rom_chips[0x8000][address - 0x8000]
                if 0xE000 <= address <= 0xFFFF and 0xE000 in self.cartridge.rom_chips:
                    return self.cartridge.rom_chips[0xE000][address - 0xE000]
            # GAME=1, EXROM=1 (Standard cartridge)
            elif self.cartridge.game and self.cartridge.exrom:
                if 0x8000 <= address <= 0x9FFF and 0x8000 in self.cartridge.rom_chips:
                    return self.cartridge.rom_chips[0x8000][address - 0x8000]

        # Standard memory map
        if 0xA000 <= address <= 0xBFFF:
            if self.cartridge and not self.cartridge.exrom and 0xA000 in self.cartridge.rom_chips:
                return self.cartridge.rom_chips[0xA000][address - 0xA000]
            if loram: return self.basic_rom[address - 0xA000]
        elif 0xD000 <= address <= 0xDFFF:
            if loram and hiram and charen:
                if 0xD000 <= address <= 0xD3FF: return self.vic.read(address)
                if 0xD400 <= address <= 0xD7FF: return self.sid.read(address)
                if 0xDC00 <= address <= 0xDCFF: return self.cia1.read(address)
                if 0xDD00 <= address <= 0xDDFF: return self.cia2.read(address)
                if 0xD800 <= address <= 0xDBFF: return self.ram[address]
        elif 0xE000 <= address <= 0xFFFF:
            if hiram: return self.kernal_rom[address - 0xE000]

        # Default to RAM read
        return self.ram[address]

    def load_basic_rom_from_file(self, filename):
        """Loads the C64 BASIC ROM into its dedicated memory."""
        try:
            with open(filename, 'rb') as f:
                rom_data = f.read()
                if len(rom_data) != 0x2000: # 8KB
                    print(f"Warning: BASIC ROM '{filename}' is not 8KB. Size: {len(rom_data)} bytes.")
                for i, byte in enumerate(rom_data):
                    self.basic_rom[i] = byte
            print(f"Loaded BASIC ROM '{filename}' ({len(rom_data)} bytes) at $A000.")
        except FileNotFoundError:
            print(f"Error: BASIC ROM file '{filename}' not found. C64 emulation will be incomplete.")

    def load_kernal_rom_from_file(self, filename):
        """Loads the C64 KERNAL ROM into its dedicated memory."""
        try:
            with open(filename, 'rb') as f:
                rom_data = f.read()
                if len(rom_data) != 0x2000: # 8KB
                    print(f"Warning: KERNAL ROM '{filename}' is not 8KB. Size: {len(rom_data)} bytes.")
                for i, byte in enumerate(rom_data):
                    self.kernal_rom[i] = byte
            print(f"Loaded KERNAL ROM '{filename}' ({len(rom_data)} bytes) at $E000.")
        except FileNotFoundError:
            print(f"Error: KERNAL ROM file '{filename}' not found. C64 emulation will be incomplete.")

    def __getitem__(self, address):
        return self.read(address)

    def load_prg(self, filename):
        """Loads a .prg file into memory."""
        try:
            with open(filename, 'rb') as f:
                # First two bytes are the little-endian load address
                load_address_lsb = f.read(1)[0]
                load_address_msb = f.read(1)[0]
                load_address = (load_address_msb << 8) | load_address_lsb

                program_data = f.read()
                for i, byte in enumerate(program_data):
                    self.write(load_address + i, byte)
                
                print(f"Loaded .prg file '{filename}' ({len(program_data)} bytes) at ${load_address:04X}.")
                return load_address
        except FileNotFoundError:
            print(f"Error: .prg file '{filename}' not found.")
            return None

    def load_crt(self, filename):
        """Loads a .crt cartridge file."""
        try:
            self.cartridge = Cartridge()
            self.cartridge.load_from_crt(filename)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error loading cartridge: {e}")
            self.cartridge = None

    def load_program(self, start_address, program_data):
        """Loads a program into RAM at a specific address."""
        for i, byte in enumerate(program_data):
            self.write(start_address + i, byte)

    def load_rom_from_file(self, filename, start_address):
        """Loads a binary ROM file into RAM."""
        try:
            with open(filename, 'rb') as f:
                rom_data = f.read()
                self.load_program(start_address, rom_data)
            print(f"Loaded '{filename}' ({len(rom_data)} bytes) at address ${start_address:04X}.")
        except FileNotFoundError:
            print(f"Error: ROM file '{filename}' not found.")
            exit(1)