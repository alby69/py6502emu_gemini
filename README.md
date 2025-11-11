# pyC64emu: Un Emulatore di Commodore 64 in Python

Questo progetto è un emulatore per il Commodore 64 basato su Python. L'obiettivo è creare un'emulazione semplice, comprensibile ed estensibile del classico computer a 8 bit, inclusa la sua CPU MOS 6510, i chip custom e un'interfaccia grafica completa.

Questo progetto è stato sviluppato con l'assistenza di Gemini Code Assist, che ha eseguito il refactoring e l'estensione di una versione iniziale per renderla più modulare, accurata e completa di funzionalità, inclusa un'interfaccia utente grafica.

## Funzionalità Principali dell'Emulatore

L'emulatore attualmente supporta un'ampia gamma delle capacità del C64:

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
    *   Interrupt software tramite l'istruzione `BRK`.
*   **Decimal Mode**: Accurate Binary-Coded Decimal (BCD) arithmetic for `ADC` and `SBC` instructions when the decimal flag is set.
*   **Architettura Modulare**: Una netta separazione tra `CPU`, `Bus`, `MemoryManager` e periferiche, che consente un'espansione più semplice.
*   **Superamento Test Funzionali**: L'emulatore supera con successo il test funzionale completo `6502_functional_test.bin` di Klaus Dormann.

## Graphical User Interface (GUI)

The emulator includes an interactive GUI built with `pygame`, providing a real-time debugging and visualization experience focused on performance.

### GUI Features

*   **Schermo C64**: Rendering diretto dell'output video del VIC-II.
*   **Finestra Ridimensionabile**: La finestra principale può essere ridimensionata liberamente e lo schermo del C64 si adatterà proporzionalmente mantenendo il rapporto d'aspetto.
*   **Pannello Info Live**: Una visualizzazione in tempo reale di:
    *   **Interfaccia a Pagine**: Il pannello informativo è organizzato in pagine. Usa il tasto `Tab` per scorrerle.
    *   **Stato CPU**: Vista live dei registri (PC, A, X, Y, SP) e dei flag di stato. Include un editor per modificare i valori dei registri.
    *   **Disassembly**: A live disassembly view centered on the current Program Counter.
    *   **Memory Viewer**: A hex dump of memory with an ASCII representation. Includes an editor to write values directly to memory.
    *   **Audio Visualizers**: An oscilloscope for the raw waveform and a spectrum analyzer for frequency content.
    *   **Performance**: A live FPS (Frames Per Second) counter.
*   **Keyboard Controls**:
    *   `Tab`: Cycle through the info panel pages.
    *   `F1`: Show or hide the in-emulator help screen.
    *   `F2`: Mostra/nascondi i visualizzatori audio.
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

Il progetto è organizzato in una libreria `pyc64` e uno script di avvio:

*   `main.py`: L'entry point principale dell'applicazione. Contiene tutto il codice per la GUI `pygame` e orchestra l'emulatore.
*   `pyc64/`: La directory della libreria principale dell'emulatore.
    *   `cpu.py`: Contiene la classe `CPU` principale, che gestisce la decodifica delle istruzioni, l'esecuzione, la gestione dei flag e la logica degli interrupt. Include anche un potente debugger.
    *   `bus.py`: Implementa la classe `Bus`, che collega la CPU, la memoria e le periferiche.
    *   `memory.py`: Contiene il `MemoryManager`, che gestisce la mappa di memoria del C64, inclusa la RAM, le ROM e la logica di **bank switching**.
    *   `opcodes.py`: Definizioni statiche per tutti gli opcode del 6502.
    *   `peripherals/`: Sottodirectory per i chip custom del C64 (`vic.py`, `sid.py`, `cia.py`).
*   `system.py`: Uno script semplice e senza GUI per eseguire l'emulatore, utilizzato principalmente per test funzionali da riga di comando.
*   `roms/`: Directory contenente i file ROM del C64.

## How to Run

1.  **Install Dependencies**: Ensure you have Python 3 installed. Then, install the required libraries using pip:
    ```bash
    pip install pygame numpy imageio imageio-ffmpeg
    ```

2.  **Get the ROMs**: Place the required Commodore 64 ROM files in the `roms/` directory. You will need:
    *   `basic.rom` (8KB)
    *   `kernal.rom` (8KB)
    *   `char.rom` (4KB)
3.  **Run the Emulator**: Open a terminal or command prompt, navigate to the project directory, and execute the `main.py` script:
    ```bash
    python main.py
    ```
The GUI will launch and automatically start the C64 at the BASIC `READY.` prompt.

To load and run a `.prg` file, either drag and drop it onto the window or pass its filename as a command-line argument:
```bash
python main.py your_program.prg
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