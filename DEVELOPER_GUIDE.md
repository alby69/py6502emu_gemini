# Developer's Guide: Adding New Peripherals

This guide explains how to add a new memory-mapped peripheral to the pyC64emu project. The emulator's modular design makes it straightforward to extend its hardware capabilities.

## 1. Core Architecture Overview

The emulator's architecture is centered around the `Bus` class, which acts as a central hub connecting the `CPU` to all other components.

```
  [ CPU ] <--> [ Bus ] <--> [ RAM, VIC-II, SID, CIA, Cartridge, ... ]
```

When the CPU executes a `read` or `write` operation, it calls the corresponding method on the `Bus`. The `Bus` is then responsible for determining which component (RAM or a specific peripheral) should handle the request based on the memory address.

## 2. The Peripheral "Contract"

To integrate smoothly with the emulator, a new peripheral should be implemented as a Python class that follows a simple "contract" by providing a standard set of methods.

Here is a basic template for a new peripheral class:

```python
class MyNewPeripheral:
    def __init__(self, bus, cpu=None):
        self.bus = bus
        self.cpu = cpu # Optional, only needed if the peripheral can trigger interrupts
        # Initialize internal state, registers, etc.
        self.registers = [0x00] * 16

    def read(self, address):
        """Handle CPU reads from this peripheral's memory range."""
        local_addr = address & 0x0F # Example for a 16-byte peripheral
        # Logic to return the correct register value
        return self.registers[local_addr]

    def write(self, address, data):
        """Handle CPU writes to this peripheral's memory range."""
        local_addr = address & 0x0F
        # Logic to update internal state based on the write
        self.registers[local_addr] = data

    def save_state(self):
        """Return a JSON-serializable dictionary of the peripheral's state."""
        return {
            'registers': self.registers,
            # ... other state variables ...
        }

    def restore_state(self, state):
        """Restore the peripheral's state from a dictionary."""
        self.registers = state['registers']
        # ... restore other state variables ...
```

## 3. Integrating with the Bus

Once your peripheral class is created, you need to "plug it into" the `Bus`.

#### Step 1: Instantiate the Peripheral in `bus.py`

In the `Bus.__init__` method, create an instance of your new class.

```python
# in bus.py
class Bus:
    def __init__(self, cpu=None):
        # ... existing initializations ...
        self.my_peripheral = MyNewPeripheral(self, cpu=self.cpu)
```

#### Step 2: Map its Address Range in `bus.py`

Modify the `Bus.read()` and `Bus.write()` methods to delegate memory access to your peripheral when the address falls within its designated range. **The order of these checks is important**, as some peripherals (like cartridges) can override others.

```python
# in bus.py -> Bus.read()

    def read(self, address):
        # ... other mapping logic ...

        # Add your peripheral's range
        if 0xDE00 <= address <= 0xDEFF:
            return self.my_peripheral.read(address)

        # ... other mapping logic ...

        # Default to RAM read
        return self.ram[address]
```

## 4. Example: Adding a New Cartridge Type

Let's say we want to add support for a hypothetical "SuperCart" (Type 10) that maps an 8KB ROM to `$C000-$DFFF`.

#### Step 1: Update the `Cartridge` class in `bus.py`

First, we would update the `load_from_crt` method to recognize the new type.

#### Step 2: Update the `Bus.read()` method

Next, we would add a new condition in `Bus.read()` to handle this cartridge's specific memory mapping. This check should come *before* the standard I/O check for the `$D000` range, as the cartridge takes priority.

```python
# in bus.py -> Bus.read()

    def read(self, address):
        # ...
        if self.cartridge:
            # Add logic for our new cartridge type
            if self.cartridge.type == 10 and 0xC000 <= address <= 0xDFFF:
                return self.cartridge.rom_chips[0xC000][address - 0xC000]
            
            # ... existing cartridge logic ...
        # ...
```

By following these steps, you can integrate any new memory-mapped device into the emulator, extending its functionality while keeping the overall architecture clean and modular.