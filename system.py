from cpu_6502 import *
from bus import Bus

# --- Main Program ---
bus = Bus()
cpu = CPU(bus)

# --- C64 ROM Loading ---
print("Loading C64 ROMs...")
bus.load_basic_rom_from_file("c64_basic.rom")
bus.load_kernal_rom_from_file("c64_kernal.rom")

# Set PC to C64 KERNAL reset vector (read from $FFFC/$FFFD)
# For now, we'll hardcode the typical entry point after reset.
# A proper reset sequence would read $FFFC/$FFFD.
cpu.pc = 0xFCE2 # Typical KERNAL cold start entry point
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
