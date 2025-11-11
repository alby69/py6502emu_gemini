# py6502emu: A 6502 CPU Emulator in Python

This project is a Python-based emulator for the MOS Technology 6502 microprocessor. The goal is to create a simple, understandable, and extensible emulation of the classic 8-bit CPU that powered legendary systems like the Commodore 64, Apple II, and Nintendo Entertainment System.

This project was developed with the assistance of Gemini Code Assist, refactoring and extending an initial version to be more modular, accurate, and feature-complete, including a full-featured graphical user interface.

## Core Emulator Features

The emulator currently supports a wide range of the 6502's capabilities:

*   **Full Official Instruction Set**: All 56 official instructions are implemented.
*   **Cycle-Accurate Emulation**: The emulator is cycle-accurate for all official and most common undocumented instructions, including variable timings for branches and page-boundary crossings.
*   **All Documented Addressing Modes**:
    *   Immediate, Implied, Accumulator
    *   Absolute, Absolute X/Y
    *   Zero Page, Zero Page X/Y
    *   Relative
    *   Indirect, Indirect X/Y
*   **Common Undocumented Opcodes**: Includes implementations for popular "illegal" opcodes like `SLO`, `RLA`, `SAX`, `LAX`, and `DCP`.
*   **Interrupt Handling**:
    *   Non-Maskable Interrupts (NMI)
    *   Standard Interrupt Requests (IRQ)
    *   Software interrupts via the `BRK` instruction.
*   **Decimal Mode**: Accurate Binary-Coded Decimal (BCD) arithmetic for `ADC` and `SBC` instructions when the decimal flag is set.
*   **Modular Architecture**: A clean separation between the `CPU` and the system `Bus`, allowing for easier expansion.
*   **Functional Test Success**: The emulator successfully passes Klaus Dormann's comprehensive `6502_functional_test.bin`.

## Graphical User Interface (GUI)

The emulator includes an interactive GUI built with `pygame`, providing a real-time debugging and visualization experience focused on performance.

### GUI Features

*   **C64 Screen Display**: A direct rendering of the VIC-II video output.
*   **Resizable Window**: The main window can be freely resized, and the C64 screen display will scale proportionally while maintaining its aspect ratio.
*   **Live Info Panel**: A real-time display of:
    *   **Paged Interface**: The info panel is organized into pages. Use the `Tab` key to cycle through them.
    *   **CPU State**: Live view of registers (PC, A, X, Y, SP) and status flags. Includes an editor to modify register values.
    *   **Disassembly**: A live disassembly view centered on the current Program Counter.
    *   **Memory Viewer**: A hex dump of memory with an ASCII representation. Includes an editor to write values directly to memory.
    *   **Audio Visualizers**: An oscilloscope for the raw waveform and a spectrum analyzer for frequency content.
    *   **Performance**: A live FPS (Frames Per Second) counter.
*   **Keyboard Controls**:
    *   `Tab`: Cycle through the info panel pages.
    *   `F1`: Show or hide the in-emulator help screen.
    *   `F2`: Toggle visibility of the audio visualizers.
    *   `F5`: Toggle Run/Stop for the emulation.
    *   `F4`: Hold to rewind the emulation state. A flashing border indicates when rewind is active.
    *   `F6`: Execute a single CPU step (when stopped).
    *   `F7`-`F12`: Load emulator state from the corresponding slot (`pyc64_state_1.json` - `pyc64_state_6.json`).
    *   `Shift`+`F7`-`Shift`+`F12`: Save emulator state to the corresponding slot.
    *   `F9`: Start or stop recording a video (`pyc64_recording.mp4`).
    *   `F10`: Save a screenshot (`pyc64_screenshot_*.png`).
    *   `F11`: Toggle Turbo Mode (runs emulation as fast as possible).
    *   `F12`: Reset the emulator.
*   **Joystick Support**:
    *   Automatically detects and uses the first connected physical joystick for Port 2.
    *   **Keyboard Emulation**: For users without a joystick, the numeric keypad is mapped to joystick directions, and Right `Ctrl` is mapped to the fire button.
*   **Drag and Drop**: Load a `.prg` file by dragging it from your file explorer and dropping it onto the emulator window.

## Project Structure

The project is organized into the following files:

*   `gui.py`: The main entry point for the application. It contains all the code for the `tkinter` GUI and orchestrates the emulator.
*   `cpu_6502.py`: Contains the core `CPU` class, which handles instruction decoding, execution, flag management, and interrupt logic. It also includes a powerful command-line debugger.
*   `bus.py`: Implements the `Bus` class, which manages the system's 64KB memory space and provides a simple read/write interface for the CPU.
*   `system.py`: A simple, non-GUI script for running the emulator, primarily used for running functional tests from the command line.
*   `6502_functional_test.bin`: The binary for Klaus Dormann's 6502 functional test ROM, used to verify the accuracy of the CPU implementation.

## How to Run

1.  **Install Dependencies**: Ensure you have Python 3 installed. Then, install the required libraries using pip:
    ```bash
    pip install pygame numpy imageio imageio-ffmpeg
    ```
    *Note: `imageio-ffmpeg` is required for video recording.*

2.  **Get the ROMs**: Place the required Commodore 64 ROM files in the same directory as the project files. You will need:
    *   `c64_basic.rom` (8KB)
    *   `c64_kernal.rom` (8KB)
    *   `char.rom` (4KB)
3.  **Run the Emulator**: Open a terminal or command prompt, navigate to the project directory, and execute the `gui.py` script:
    ```bash
    python gui.py
    ```
The GUI will launch and automatically start the C64 at the BASIC `READY.` prompt.

To load and run a `.prg` file, either drag and drop it onto the window or pass its filename as a command-line argument:
```bash
python gui.py your_program.prg
```

## Command-Line Debugger

In addition to the GUI, a powerful command-line debugger is built into the `CPU` class. It can be used with `system.py` or by modifying the GUI code to trigger `cpu.debug_prompt()`.
### Debugger Commands

| Command(s) | Description | Example |
| --- | --- | --- |
| `s`, `step` | Execute the next instruction. | `s` |
| `c`, `continue` | Continue execution until the next breakpoint. | `c` |
| `b <addr>` | Set a breakpoint at a hex address. | `b 8000` |
| `b clear <addr>`| Clear a specific breakpoint. | `b clear 8000` |
| `b clear all` | Clear all breakpoints. | `b clear all` |
| `blist`, `breakpoints` | List all active breakpoints. | `blist` |
| `flags` | Show a detailed, multi-line view of all CPU flags. | `flags` |
| `stack` | Display the current contents of the stack. | `stack` |
| `bt`, `callstack`| Show a simulated call stack backtrace. | `bt` |
| `cycles` | Show the total number of elapsed CPU cycles. | `cycles` |
| `m <addr> [len]`| Display a hex dump of memory. | `m 0200 64` |
| `dasm <addr> [n]`| Disassemble `n` instructions from an address. | `dasm C000 10` |
| `find <b1>...` | Search for a sequence of bytes in memory. | `find A9 20 85` |
| `set <addr> <val>`| Write a value to a memory address. | `set 0200 FF` |
| `reg <reg> <val>`| Modify a CPU register (a, x, y, pc, sp). | `reg pc C000` |
| `save [file]` | Save the complete emulator state to a file. | `save state1.json` |
| `load [file]` | Restore the emulator state from a file. | `load state1.json` |
| `trace` | Toggle instruction tracing to `trace.log`. | `trace` |
| `autodasm` | Toggle automatic disassembly on break. | `autodasm` |
| `h`, `help` | Show the list of available commands. | `h` |

For a hands-on example, see the **Debugger Tutorial: Analyzing a BASIC Program**.

## Extending the Emulator

The emulator is designed to be modular, making it easy to add new peripherals or hardware features. For a detailed guide on how to extend the emulator, please see the **Developer's Guide: Adding New Peripherals**.

---

## Suggested Future Improvements

This emulator provides a solid foundation, but there are many exciting ways it could be improved and expanded into a full-fledged system emulator.

### 1. Memory-Mapped I/O and Peripherals

*   **How**: Enhance the `Bus` class's `read` and `write` methods to check if an address falls within a range belonging to a peripheral (like a PPU for graphics or an APU for sound). If so, it would delegate the read/write call to that peripheral's object.
*   **Why**: This is the key to building a complete system emulator that can handle graphics, sound, and input.

### 2. ROM Loading and System Integration

*   **How**: Modify the `Bus` class to include a method for loading a binary ROM file (e.g., a `.nes` or `.prg` file) into a specific memory range. You would also need to set the CPU's program counter to the ROM's reset vector.
*   **Why**: This would allow the emulator to run actual software from classic systems. **(Note: This is already implemented for a generic binary format.)**

---
## C64 Emulation Roadmap & Status

This project has evolved into a feature-rich Commodore 64 emulator. Here is the current status of the major components.

### 2. VIC-II (Video Interface Chip) Emulation

*   **Description**: This is the heart of C64 graphics. The VIC-II chip reads from system memory to generate the video signal, including characters, bitmaps, and sprites.
*   **Implementation**:
    *   Emulate the VIC-II's 47 registers that control screen modes, colors, and memory pointers.
    *   Write a rendering loop that simulates the VIC-II's line-by-line screen drawing process.
*   **Status**: **Largely Complete.** The VIC-II emulation is highly advanced and supports:
    *   Standard text mode.
    *   Standard single-color bitmap mode.
    *   Rendering for all 8 hardware sprites.
    *   Support for both single-color and multicolor sprite modes.
    *   X and Y sprite expansion.
    *   Sprite-to-background priority, controlled by VIC-II register `$D01B`.
    *   Sprite-to-data and sprite-to-sprite collision detection and interrupt generation.
    *   Smooth horizontal and vertical scrolling, controlled by VIC-II registers `$D016` and `$D011`.
    *   "Badline" timing simulation for accurate raster effects.

### 3. CIA (Complex Interface Adapter) Emulation

*   **Description**: The two CIA chips handle most of the C64's input and output, including reading the keyboard and joysticks, and managing system timers.
*   **Implementation**:
    *   Emulate the CIA registers.
    *   Map PC keyboard events to the C64's keyboard matrix.
    *   Implement the CIA timers, which are crucial for system timing (e.g., the jiffy interrupt).
*   **Status**: **Largely Complete.** Keyboard input is functional, joystick input for Port 2 is supported (both physical and keyboard-emulated), and CIA Timer A is implemented. This is sufficient to drive the C64's main system interrupt (the "jiffy"), making the cursor blink and BASIC usable.

### 4. SID (Sound Interface Device) Emulation
*   **Disk Drive Emulation**: High-level emulation of a 1541 disk drive. Supports loading `.prg` files from `.d64` disk images via the standard KERNAL `LOAD` command. A file dialog can be used to attach disk images.

*   **Description**: The SID chip is a three-voice synthesizer responsible for the C64's iconic sound. Emulating it accurately is a complex task.
*   **Implementation**:
    *   Emulate the SID's registers for controlling oscillators, filters, and envelopes.
    *   Create a sound synthesis engine that generates audio samples based on the register settings.
*   **Status**: **Largely Complete.** The SID emulation is quite advanced and supports:
    *   Three independent voices.
    *   Triangle, Sawtooth, Pulse, and Noise waveforms for each voice.
    *   A more accurate ADSR envelope generator for each voice.
    *   A multi-mode (Low-pass, Band-pass, High-pass) resonant filter.
    *   Master volume control.
    *   External audio input mixing.
    *   Reading of Voice 3's oscillator and envelope output.

## Next Major Goal: Bank Switching

*   **Description**: The C64's memory map is highly dynamic. The CPU can swap out the BASIC and KERNAL ROMs, as well as the I/O chips, to make the underlying RAM accessible. This is controlled by the 6502's processor port at memory location `$01`.
*   **Implementation**:
    *   Modify the `Bus` class's `read` and `write` methods to check the bits of `$01`.
    *   Based on these bits, the `Bus` must decide whether to access RAM, BASIC ROM, KERNAL ROM, or I/O chips in the `$A000-$BFFF` and `$E000-$FFFF` regions.
*   **Status**: **Not yet implemented.** The emulator currently uses a fixed memory map where ROMs and I/O are always visible. Implementing bank switching is the most critical next step for broad software compatibility.