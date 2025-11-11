from pyc64.cpu import CPU
from pyc64.bus import Bus

# --- Main Program ---
cpu = CPU(None)
bus = Bus(cpu)
cpu.bus = bus

# --- C64 ROM Loading ---
print("Loading C64 ROMs...")
bus.load_rom_from_file("roms/basic.rom", "basic")
bus.load_rom_from_file("roms/kernal.rom", "kernal")
bus.vic.load_char_rom("roms/char.rom")

# Set PC to C64 KERNAL reset vector (read from $FFFC/$FFFD)
cpu.pc = (bus.read(0xFFFC) | (bus.read(0xFFFD) << 8))
print(f"CPU PC set to C64 KERNAL reset vector: ${cpu.pc:04X}")

# --- Optional: Klaus Dormann's 6502 Functional Test Program ---
# Uncomment the lines below if you want to run the functional test instead of C64 ROMs.
# bus.load_rom_from_file("6502_functional_test.bin", 0x0000)
# cpu.pc = 0x0400 # Test entry point
# print("Loaded 6502_functional_test.bin, entry point at $0400")
# success_address = 0x3469 # Test success address
# cpu.breakpoints.add(success_address)
# print(f"A breakpoint is set at the success address: ${success_address:04X}.")

print(f"Starting C64 emulation...")

while True:
    cpu.tick()
