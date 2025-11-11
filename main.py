import pygame

from pyc64.cpu import CPU
from pyc64.bus import Bus
from pyc64.peripherals.cia import C64_KEY_MAP # Import the key mapping
import numpy as np
import sys
import datetime
import imageio

NUM_SAVE_SLOTS = 6 # Number of save state slots (F7-F12)
SAVE_STATE_FILENAMES = [f"pyc64_state_{i}.json" for i in range(1, NUM_SAVE_SLOTS + 1)]

EMU_VERSION = "0.9.0" # Current emulator version
REPO_URL = "https://github.com/aabate/py6502emu_gemini" # Placeholder for project repository

class EmulatorGUI:
    def __init__(self):
        pygame.init()

        # --- Emulator Setup ---
        self.cpu = CPU(None) # Bus will be created in reset_and_load
        self.bus = Bus(self.cpu)
        self.cpu.bus = self.bus
        self.running = True # Start the emulator in a running state

        # --- Pygame Audio Setup ---
        pygame.mixer.pre_init(44100, -16, 2, 512) # SampleRate, BitSize, 2 Channels (Stereo), BufferSize
        pygame.mixer.init()

        # --- Pygame Setup ---
        self.C64_SCREEN_WIDTH = 320
        self.C64_SCREEN_HEIGHT = 200
        self.INFO_PANEL_WIDTH = 350
        self.WINDOW_WIDTH = self.C64_SCREEN_WIDTH + self.INFO_PANEL_WIDTH
        self.initial_c64_width = self.C64_SCREEN_WIDTH
        self.initial_c64_height = self.C64_SCREEN_HEIGHT
        self.WINDOW_HEIGHT = 600 # Adjusted for paginated info panel
        
        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("pyC64emu - A Pygame based C64 Emulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 15)

        # --- Colors ---
        self.COLOR_BG = (40, 40, 40)
        self.COLOR_FG = (220, 220, 220)
        self.COLOR_HL = (255, 255, 0) # Highlight for current PC

        # --- Video Recording State ---
        self.is_recording = False
        self.video_writer = None
        self.video_filename = "pyc64_recording.mp4"
        self.turbo_mode = False
        self.audio_buffer_for_vis = None
        self.show_visualizers = True

        # Register Editor State
        self.reg_edit_pc = ""
        self.reg_edit_a = ""
        self.reg_edit_x = ""
        self.reg_edit_y = ""
        self.reg_edit_sp = ""
        # Info Panel Paging and Memory Viewer State
        self.info_pages = ["CPU State", "Disassembly", "Memory Viewer", "Visualizers", "Controls"]
        self.current_info_page_index = 0
        self.show_help_screen = False

        prg_file_to_load = sys.argv[1] if len(sys.argv) > 1 else None
        self.reset_and_load(prg_file_to_load)

    def reset_and_load(self, prg_file=None):
        """Resets the emulator and loads the C64 ROMs."""
        self.memory_view_addr = 0x0200  # Default start address for memory view
        self.cpu = CPU(None)
        self.bus = Bus(self.cpu)
        self.cpu.bus = self.bus
        self.running = False # Pause emulation during reset
        
        try:
            self.bus.load_rom_from_file("roms/basic.rom", "basic")
            self.bus.load_rom_from_file("roms/kernal.rom", "kernal")
            self.bus.vic.load_char_rom("roms/char.rom")

            if prg_file:
                start_address = self.bus.load_prg(prg_file)

            # Always start by reading the reset vector. This is the most accurate way.
            self.cpu.pc = (self.bus.read(0xFFFC) | (self.bus.read(0xFFFD) << 8))
            print(f"C64 is Reset. PC set to KERNAL reset vector: ${self.cpu.pc:04X}")

        except Exception as e:
            print(f"Error during ROM loading: {e}")
        self.running = True # Ensure emulator is running after a reset
        
    def run(self):
        """The main loop of the emulator."""
        app_running = True
        while app_running:
            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    app_running = False
                
                if event.type == pygame.DROPFILE:
                    self.reset_and_load(event.file)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F5: # F5 to Run/Stop
                        self.running = not self.running
                    if event.key == pygame.K_F6 and not self.running: # F6 to Step
                        self.cpu.tick()
                    if event.key == pygame.K_F9: # F9 to toggle recording
                        self.toggle_recording()
                    if event.key == pygame.K_F10: # F10 to take a screenshot
                        self.take_screenshot()
                    if event.key == pygame.K_TAB: # Tab to cycle info panel pages
                        self.current_info_page_index = (self.current_info_page_index + 1) % len(self.info_pages)

                    if event.key == pygame.K_RETURN:
                        if self.info_pages[self.current_info_page_index] == "CPU State":
                            self.set_register_value()
                
                if event.type == pygame.VIDEORESIZE:
                    # Update window dimensions
                    self.WINDOW_WIDTH, self.WINDOW_HEIGHT = event.size
                    self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.RESIZABLE) # Recreate screen with new size and RESIZABLE flag

                    # Calculate new C64 screen dimensions maintaining aspect ratio
                    # Available width for C64 screen is total width minus info panel width
                    available_c64_width = self.WINDOW_WIDTH - self.INFO_PANEL_WIDTH
                    
                    # Calculate scale factors based on available space
                    scale_factor_w = available_c64_width / self.initial_c64_width
                    scale_factor_h = self.WINDOW_HEIGHT / self.initial_c64_height
                    
                    # Use the smaller scale factor to fit both dimensions
                    scale_factor = min(scale_factor_w, scale_factor_h)
                    self.C64_SCREEN_WIDTH = int(self.initial_c64_width * scale_factor)
                    self.C64_SCREEN_HEIGHT = int(self.initial_c64_height * scale_factor)
                    
                    # Ensure minimum size for C64 screen to avoid division by zero or tiny screen
                    if self.C64_SCREEN_WIDTH < 100: self.C64_SCREEN_WIDTH = 100
                    if self.C64_SCREEN_HEIGHT < 100: self.C64_SCREEN_HEIGHT = 100

                if event.type == pygame.KEYUP:
                    if event.key in C64_KEY_MAP:
                        row, col = C64_KEY_MAP[event.key]
                        self.bus.cia1.set_key_state(row, col, False)
                        # print(f"Key {pygame.key.name(event.key)} released (C64 Row {row}, Col {col})")


                    if event.key == pygame.K_F12: # F12 to Reset
                        self.reset_and_load(sys.argv[1] if len(sys.argv) > 1 else None)

            # --- Emulation Core ---
            if self.running and not self.show_help_screen: # Pause emulation when help is shown
                # Run a batch of CPU cycles per frame to keep emulation speed stable
                # PAL C64 runs at 985248 cycles per second. At 60fps, that's ~16420 cycles/frame.
                cycles_per_frame = 16420 
                for _ in range(cycles_per_frame):
                    self.cpu.tick()
                
                # --- Audio ---
                # Generate and play a short audio buffer only when running
                audio_buffer = self.bus.sid.generate_audio_buffer(735) # 44100 / 60fps
                self.audio_buffer_for_vis = audio_buffer # Store for visualizer
                audio_buffer = np.repeat(audio_buffer[:, np.newaxis], 2, axis=1)
                sound = pygame.sndarray.make_sound(audio_buffer)
                sound.play()

            # --- Drawing ---
            self.screen.fill(self.COLOR_BG)

            # Always draw the main screen and info panel
            c64_screen_surface = self.bus.vic.get_screen_surface()
            scaled_c64_surface = pygame.transform.scale(c64_screen_surface, (self.C64_SCREEN_WIDTH, self.C64_SCREEN_HEIGHT))
            self.screen.blit(scaled_c64_surface, (0, 0))
            self.draw_info_panel(self.C64_SCREEN_WIDTH + 10)

            # If help is active, draw it as an overlay
            if self.show_help_screen:
                self.draw_help_screen()

            pygame.display.flip()

            # --- Video Recording ---
            if self.is_recording and self.video_writer:
                # Grab the frame from the screen
                frame_data = pygame.surfarray.array3d(self.screen)
                # imageio expects (height, width, channels), pygame gives (width, height, channels)
                # so we need to transpose it.
                frame_data = frame_data.transpose([1, 0, 2])
                self.video_writer.append_data(frame_data)

    def draw_info_panel(self, x_start_offset):
        x_offset = x_start_offset
        y_offset = 10
        
        # Draw Page Title
        y_offset = self.draw_text(f"--- {self.info_pages[self.current_info_page_index]} ---", x_offset, y_offset, self.COLOR_HL)
        y_offset += 5

        # --- Performance ---
        fps_text = f"FPS: {self.clock.get_fps():.1f}"
        y_offset = self.draw_text(fps_text, x_offset, y_offset)
        y_offset += 5

        # --- Registers ---
        current_page_name = self.info_pages[self.current_info_page_index]

        if current_page_name == "CPU State":
            y_offset = self.draw_text(f"PC: ${self.cpu.pc:04X}", x_offset, y_offset)
            y_offset = self.draw_text(f"A:  ${self.cpu.a:02X}", x_offset, y_offset)
            y_offset = self.draw_text(f"X:  ${self.cpu.x:02X}", x_offset, y_offset)
            y_offset = self.draw_text(f"Y:  ${self.cpu.y:02X}", x_offset, y_offset)
            y_offset = self.draw_text(f"SP: ${self.cpu.sp:02X}", x_offset, y_offset)
            y_offset += 5

            # --- Flags ---
            flags_str = (
                ('N' if self.cpu.n else '-') +
                ('V' if self.cpu.v else '-') +
                '-' +
                ('B' if self.cpu.b else '-') +
                ('D' if self.cpu.d else '-') +
                ('I' if self.cpu.i else '-') +
                ('Z' if self.cpu.z else '-') +
                ('C' if self.cpu.c else '-')
            )
            y_offset = self.draw_text("--- Flags ---", x_offset, y_offset)
            y_offset = self.draw_text(f"NV-BDIZC", x_offset, y_offset)
            y_offset = self.draw_text(flags_str, x_offset, y_offset)
            y_offset += 5

            # --- Cycles ---
            y_offset = self.draw_text("--- Cycles ---", x_offset, y_offset)
            y_offset = self.draw_text(f"{self.cpu.total_cycles}", x_offset, y_offset)
            y_offset += 5

        elif current_page_name == "Disassembly":
            addr = self.cpu.pc
            # Show a few instructions before the PC
            start_addr = max(0, addr - 10)
            temp_addr = start_addr
            
            for i in range(20): # Show 20 instructions
                if temp_addr > 0xFFFF:
                    break
                
                line = self.disassemble_line(temp_addr)
                is_current_pc = (temp_addr == self.cpu.pc)
                y_offset = self.draw_text(line, x_offset, y_offset, self.COLOR_HL if is_current_pc else self.COLOR_FG)

                opcode = self.bus.read(temp_addr)
                if opcode in self.cpu.commands:
                    mode = self.cpu.commands[opcode]['m']
                    temp_addr += self.cpu.increments.get(mode, 1)
                else:
                    temp_addr += 1

        elif current_page_name == "Memory Viewer":
            y_offset = self.draw_text(f"Current Address: ${self.memory_view_addr:04X}", x_offset, y_offset)
            y_offset += 5

            # Display 16 rows of 16 bytes each (256 bytes total)
            for i in range(16):
                start_addr = self.memory_view_addr
                addr = start_addr + (i * 16)
                if addr > 0xFFFF:
                    break
                
                line_hex = f"${addr:04X}: "
                hex_part = []
                ascii_part = []
                for j in range(16):
                    byte_addr = addr + j
                    if byte_addr <= 0xFFFF:
                        byte = self.bus.read(byte_addr)
                        hex_part.append(f"{byte:02X}")
                        ascii_part.append(chr(byte) if 0x20 <= byte <= 0x7E else '.')
                    else:
                        hex_part.append("  ")
                        ascii_part.append(" ")
                
                line_hex += ' '.join(hex_part) + " |" + ''.join(ascii_part) + "|"
                y_offset = self.draw_text(line_hex, x_offset, y_offset)
            
            y_offset += 5
            y_offset = self.draw_text("PgUp/PgDown to scroll", x_offset, y_offset)

        elif current_page_name == "Visualizers":
            if self.show_visualizers:
                # --- Audio Visualizer ---
                y_offset = self.draw_text("--- Spectrum ---", x_offset, y_offset)
                self.draw_visualizer(x_offset, y_offset)
                y_offset += 90 # Reserve space for the visualizer

                # --- Oscilloscope ---
                y_offset += 10
                y_offset = self.draw_text("--- Waveform ---", x_offset, y_offset)
                self.draw_oscilloscope(x_offset, y_offset)
                y_offset += 90 # Reserve space for the oscilloscope
            else:
                y_offset = self.draw_text("Visualizers are hidden (F2 to toggle)", x_offset, y_offset)

        elif current_page_name == "Controls":
            run_status = "Running" if self.running else "Stopped"
            y_offset = self.draw_text(f"F5: Toggle Run ({run_status})", x_offset, y_offset)

            y_offset = self.draw_text("F6: Step (when stopped)", x_offset, y_offset)
            rec_status = "ON" if self.is_recording else "OFF"
            y_offset = self.draw_text("F1: Show/Hide Help", x_offset, y_offset)
            y_offset = self.draw_text("Tab: Next Info Page", x_offset, y_offset)
            for i in range(NUM_SAVE_SLOTS):
                slot_number = i + 1
                y_offset = self.draw_text(f"F{slot_number+6}: Load State {slot_number}", x_offset, y_offset)
                y_offset = self.draw_text(f"S+F{slot_number+6}: Save State {slot_number}", x_offset, y_offset)
            y_offset = self.draw_text("PgUp/PgDown: Scroll Memory Viewer", x_offset, y_offset)


            vis_status = "ON" if self.show_visualizers else "OFF"
            y_offset = self.draw_text(f"F2: Toggle Visualizers ({vis_status})", x_offset, y_offset)
            turbo_status = "ON" if self.turbo_mode else "OFF"
            y_offset = self.draw_text(f"F11: Toggle Turbo Mode ({turbo_status})", x_offset, y_offset)
            y_offset = self.draw_text(f"F9: Record Video ({rec_status})", x_offset, y_offset)
            y_offset = self.draw_text("F10: Take Screenshot", x_offset, y_offset)
            y_offset = self.draw_text("F12: Reset Emulator", x_offset, y_offset)

    def draw_register_editor(self, x, y):
        """Draws the CPU register editor on the info panel."""
        # Define the positions for the register labels and input boxes
        reg_x = x
        input_x = x + 50
        button_x = x + 120

        # Draw the register labels and input boxes
        pygame.draw.rect(self.screen, self.COLOR_FG, (input_x, y - 3, 50, 18), 1)
        text_surface = self.font.render(self.reg_edit_pc, True, self.COLOR_FG)
        self.screen.blit(text_surface, (input_x + 5, y))
        y += 20

        pygame.draw.rect(self.screen, self.COLOR_FG, (input_x, y - 3, 50, 18), 1)
        text_surface = self.font.render(self.reg_edit_a, True, self.COLOR_FG)
        self.screen.blit(text_surface, (input_x + 5, y))
        y += 20

        pygame.draw.rect(self.screen, self.COLOR_FG, (input_x, y - 3, 50, 18), 1)
        text_surface = self.font.render(self.reg_edit_x, True, self.COLOR_FG)
        self.screen.blit(text_surface, (input_x + 5, y))
        y += 20

        pygame.draw.rect(self.screen, self.COLOR_FG, (input_x, y - 3, 50, 18), 1)
        text_surface = self.font.render(self.reg_edit_y, True, self.COLOR_FG)
        self.screen.blit(text_surface, (input_x + 5, y))
        y += 20

        pygame.draw.rect(self.screen, self.COLOR_FG, (input_x, y - 3, 50, 18), 1)
        text_surface = self.font.render(self.reg_edit_sp, True, self.COLOR_FG)
        self.screen.blit(text_surface, (input_x + 5, y))
        y += 20

        return y

    def set_register_value(self):
        """Sets the value of a CPU register from the input boxes."""
        try:
            if self.reg_edit_pc:
                self.cpu._set_register("pc", self.reg_edit_pc)
            if self.reg_edit_a:
                self.cpu._set_register("a", self.reg_edit_a)
            if self.reg_edit_x:
                self.cpu._set_register("x", self.reg_edit_x)
            if self.reg_edit_y:
                self.cpu._set_register("y", self.reg_edit_y)
            if self.reg_edit_sp:
                self.cpu._set_register("sp", self.reg_edit_sp)
        except ValueError:
            print("Invalid register value.")



    def draw_visualizer(self, x, y):
        """Draws a simple spectrum analyzer for the audio output."""
        if self.audio_buffer_for_vis is None:
            return

        num_bars = 32
        vis_width = self.INFO_PANEL_WIDTH - 40
        bar_spacing = 2
        bar_width = (vis_width - (num_bars - 1) * bar_spacing) / num_bars
        max_height = 80

        try:
            # Perform FFT
            fft_data = np.fft.fft(self.audio_buffer_for_vis)
            fft_magnitude = np.abs(fft_data)[:len(fft_data)//2] # We only need the first half

            # Group FFT bins into bars (logarithmic grouping can be better, but linear is simpler)
            bins_per_bar = len(fft_magnitude) // num_bars
            if bins_per_bar == 0: return

            for i in range(num_bars):
                start_bin = i * bins_per_bar
                end_bin = (i + 1) * bins_per_bar
                bar_magnitude = np.mean(fft_magnitude[start_bin:end_bin])

                bar_height = min(max_height, int((bar_magnitude / 5000.0) * max_height)) # Normalize
                pygame.draw.rect(self.screen, self.COLOR_HL, (x + i * (bar_width + bar_spacing), y + max_height - bar_height, bar_width, bar_height))
        except Exception:
            # Avoid crashing if there's an issue with FFT data
            pass

    def draw_oscilloscope(self, x, y):
        """Draws a simple oscilloscope view of the raw audio waveform."""
        if self.audio_buffer_for_vis is None:
            return

        vis_width = self.INFO_PANEL_WIDTH - 40
        max_height = 80
        mid_y = y + max_height // 2

        # Draw the center line
        pygame.draw.line(self.screen, (80, 80, 80), (x, mid_y), (x + vis_width, mid_y))

        # Prepare points for the line graph
        points = []
        num_samples = len(self.audio_buffer_for_vis)
        if num_samples == 0: return

        for i in range(vis_width):
            sample_index = int(i * num_samples / vis_width)
            sample_value = self.audio_buffer_for_vis[sample_index]
            
            # Normalize sample value (-32768 to 32767) to the height of the scope
            normalized_y = mid_y - (sample_value / 32768.0) * (max_height / 2)
            points.append((x + i, normalized_y))

        pygame.draw.lines(self.screen, self.COLOR_HL, False, points, 1)

    def draw_help_screen(self):
        """Draws the help and about screen as an overlay."""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)) # Black with alpha
        self.screen.blit(overlay, (0, 0))

        x_offset = 50
        y_offset = 50

        y_offset = self.draw_text(f"pyC64emu v{EMU_VERSION} - A Python/Pygame C64 Emulator", x_offset, y_offset, self.COLOR_HL)
        y_offset += 20
        y_offset = self.draw_text("Based on the py6502emu project by @TokyoEdtech", x_offset, y_offset)
        y_offset = self.draw_text("Extended and refactored with Gemini Code Assist.", x_offset, y_offset)
        if REPO_URL:
            y_offset = self.draw_text(f"Project Repository: {REPO_URL}", x_offset, y_offset)
        
        y_offset += 40

        y_offset = self.draw_text("--- Controls ---", x_offset, y_offset, self.COLOR_HL)
        y_offset = self.draw_text("F1:  Show/Hide this Help Screen", x_offset, y_offset)
        y_offset = self.draw_text("Tab: Cycle Info Panel Pages", x_offset, y_offset)
        y_offset = self.draw_text("F2:  Toggle Audio Visualizers", x_offset, y_offset)
        y_offset = self.draw_text("Resize Window: Scale C64 Screen", x_offset, y_offset)
        y_offset = self.draw_text("PgUp/PgDown: Scroll Memory Viewer", x_offset, y_offset)
        y_offset = self.draw_text("F5:  Toggle Run/Pause Emulation", x_offset, y_offset)
        y_offset = self.draw_text("F6:  Step one CPU instruction (when paused)", x_offset, y_offset)
        y_offset = self.draw_text("F9:  Start/Stop Video Recording", x_offset, y_offset)
        for i in range(NUM_SAVE_SLOTS):
            slot_number = i + 1
            y_offset = self.draw_text(f"F{slot_number+6}: Load State {slot_number} (pyc64_state_{slot_number}.json)", x_offset, y_offset)
        y_offset = self.draw_text("F11: Toggle Turbo Mode", x_offset, y_offset) # Moved to Controls page
        y_offset = self.draw_text("F10: Take Screenshot", x_offset, y_offset)
        y_offset = self.draw_text("F12: Reset Emulator", x_offset, y_offset)

    def toggle_recording(self):
        """Starts or stops video recording."""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        try:
            self.video_writer = imageio.get_writer(self.video_filename, fps=60, codec='libx264', quality=8)
            self.is_recording = True
            print(f"--- Started recording to '{self.video_filename}' ---")
        except Exception as e:
            print(f"Error starting video recording: {e}")
            print("Please ensure 'imageio' and 'imageio-ffmpeg' are installed (`pip install imageio imageio-ffmpeg`)")
            self.video_writer = None

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.close()
            print(f"--- Video recording saved to '{self.video_filename}' ---")
        self.is_recording = False
        self.video_writer = None

    def take_screenshot(self):
        """Saves the current screen content to a timestamped PNG file."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pyc64_screenshot_{timestamp}.png"
            pygame.image.save(self.screen, filename)
            print(f"--- Screenshot saved to '{filename}' ---")
        except Exception as e:
            print(f"Error saving screenshot: {e}")

    def save_emulator_state(self, filename):
        """Saves the complete state of the emulator."""
        was_running = self.running
        self.running = False # Pause emulation during save
        self.cpu._save_state(filename)
        self.running = was_running # Restore running state

    def load_emulator_state(self, filename="pyc64_state.json"):
        """Loads the complete state of the emulator."""
        self.running = False # Pause emulation during load
        self.cpu._restore_state(filename)

    def draw_text(self, text, x, y, color=None):
        """Renders a line of text and returns the y-offset for the next line."""
        if color is None:
            color = self.COLOR_FG
        text_surface = self.font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))
        return y + self.font.get_height()
    
    def disassemble_line(self, addr):
        """Disassembles a single instruction at a given address for the GUI."""
        from pyc64.opcodes import Mode
        opcode = self.bus.read(addr)
        
        if opcode not in self.cpu.commands:
            return f"${addr:04X}: {opcode:02X}       ???"

        mnemonic = self.cpu.commands[opcode]['f'].__name__
        mode = self.cpu.commands[opcode]['m']
        
        operand_str = ""
        num_bytes = self.cpu.increments.get(mode, 1)

        if num_bytes == 2:
            operand = self.bus.read(addr + 1)
            if mode == Mode.IMMEDIATE: operand_str = f"#${operand:02X}"
            elif mode == Mode.ZEROPAGE: operand_str = f"${operand:02X}"
            elif mode == Mode.ZEROPAGEX: operand_str = f"${operand:02X},X"
            elif mode == Mode.ZEROPAGEY: operand_str = f"${operand:02X},Y"
            elif mode == Mode.INDIRECTX: operand_str = f"(${operand:02X},X)"
            elif mode == Mode.INDIRECTY: operand_str = f"(${operand:02X}),Y"
            elif mode == Mode.RELATIVE:
                offset = operand if operand < 128 else operand - 256
                target = addr + 2 + offset
                operand_str = f"${target:04X}"
        elif num_bytes == 3:
            lsb, msb = self.bus.read(addr + 1), self.bus.read(addr + 2)
            operand = (msb << 8) | lsb
            if mode == Mode.ABSOLUTE: operand_str = f"${operand:04X}"
            elif mode == Mode.ABSOLUTEX: operand_str = f"${operand:04X},X"
            elif mode == Mode.ABSOLUTEY: operand_str = f"${operand:04X},Y"
            elif mode == Mode.INDIRECT: operand_str = f"(${operand:04X})"

        return f"${addr:04X}: {mnemonic:<4} {operand_str:<10}"

if __name__ == "__main__":
    app = EmulatorGUI()
    app.run()