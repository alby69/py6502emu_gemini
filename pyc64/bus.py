# 6502 Bus
# By @TokyoEdtech

from .peripherals.vic import VICII
from .peripherals.sid import SID
from .peripherals.cia import CIA
from .peripherals.drive import DiskDrive1541
from .memory import MemoryManager

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
        # Link to CPU for interrupts
        self.cpu = cpu

        # Memory manager handles RAM, ROMs, and bank switching
        self.memory = MemoryManager(self)

        # Track memory writes for rewind
        self.memory_dirty_flags = set()

        # Cartridge
        self.cartridge = None

        # I/O Devices (Peripherals)
        self.vic = VICII(self, cpu=self.cpu)
        self.sid = SID()
        self.cia1 = CIA("CIA1", is_cia1=True, cpu=self.cpu) # CIA1 handles keyboard
        self.cia2 = CIA("CIA2", cpu=self.cpu)
        self.drive = DiskDrive1541()

    def write(self, address, data):
        # Delegate write to the memory manager
        self.memory.write(address, data)
        # Add address to dirty flags for rewind
        self.memory_dirty_flags.add(address)

    def read(self, address):
        # Delegate read to the memory manager
        return self.memory.read(address)

    def load_rom_from_file(self, filename, rom_type):
        """Generic ROM loader."""
        try:
            with open(filename, 'rb') as f:
                rom_data = f.read()
                self.memory.load_rom(rom_type, rom_data)
            print(f"Loaded {rom_type.upper()} ROM '{filename}' ({len(rom_data)} bytes).")
        except FileNotFoundError:
            print(f"Error: {rom_type.upper()} ROM file '{filename}' not found.")

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