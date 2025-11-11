# Placeholder for the MOS Technology CIA (Complex Interface Adapter)
import pygame

# C64 Keyboard Matrix Mapping (simplified for common keys)
# This maps (pygame_key_constant) to (row, col)
C64_KEY_MAP = {
    pygame.K_1: (0, 0), pygame.K_2: (0, 1), pygame.K_3: (0, 2), pygame.K_4: (0, 3),
    pygame.K_5: (0, 4), pygame.K_6: (0, 5), pygame.K_7: (0, 6), pygame.K_8: (0, 7),
    pygame.K_q: (1, 0), pygame.K_w: (1, 1), pygame.K_e: (1, 2), pygame.K_r: (1, 3),
    pygame.K_t: (1, 4), pygame.K_y: (1, 5), pygame.K_u: (1, 6), pygame.K_i: (1, 7),
    pygame.K_a: (2, 0), pygame.K_s: (2, 1), pygame.K_d: (2, 2), pygame.K_f: (2, 3),
    pygame.K_g: (2, 4), pygame.K_h: (2, 5), pygame.K_j: (2, 6), pygame.K_k: (2, 7),
    pygame.K_z: (3, 0), pygame.K_x: (3, 1), pygame.K_c: (3, 2), pygame.K_v: (3, 3),
    pygame.K_b: (3, 4), pygame.K_n: (3, 5), pygame.K_m: (3, 6), pygame.K_COMMA: (3, 7),
    pygame.K_F3: (4, 0), pygame.K_F5: (4, 1), pygame.K_F7: (4, 2), pygame.K_F1: (4, 3),
    pygame.K_F2: (4, 4), pygame.K_F4: (4, 5), pygame.K_F6: (4, 6), pygame.K_F8: (4, 7),
    pygame.K_LSHIFT: (5, 1), pygame.K_RSHIFT: (5, 1), # Both map to C64 Left Shift
    pygame.K_LCTRL: (5, 2), pygame.K_RCTRL: (5, 2), # Both map to C64 Control
    pygame.K_SPACE: (5, 5), pygame.K_PERIOD: (5, 6), pygame.K_SLASH: (5, 7),
    pygame.K_UP: (6, 0), pygame.K_DOWN: (6, 1), pygame.K_LEFT: (6, 2), pygame.K_RIGHT: (6, 3),
    pygame.K_RETURN: (6, 4), pygame.K_BACKSPACE: (6, 5), # Backspace maps to C64 DEL
    pygame.K_ASTERISK: (6, 7), # *
    pygame.K_0: (7, 0), pygame.K_p: (7, 1), pygame.K_AT: (7, 2), pygame.K_COLON: (7, 3),
    pygame.K_SEMICOLON: (7, 4), pygame.K_PLUS: (7, 5), pygame.K_MINUS: (7, 6),
    pygame.K_HOME: (7, 7), # C64 CLR/HOME
}

class CIA:
    def __init__(self, name="CIA", is_cia1=False, cpu=None):
        self.name = name
        self.registers = [0x00] * 16
        self.is_cia1 = is_cia1
        self.cpu = cpu

        # CIA1 specific for keyboard
        if self.is_cia1:
            # Keyboard matrix: 8 rows, 8 columns.
            # Each element is 1 (not pressed) or 0 (pressed).
            # Initialized to all 1s (no keys pressed).
            self.keyboard_matrix = [[1 for _ in range(8)] for _ in range(8)]
            self.port_a_output = 0xFF # Output to keyboard columns (active low)
            self.port_b_output = 0xFF # Output to keyboard rows (active low)
            self.ddra = 0x00 # Data Direction Register A (0=input, 1=output)
            self.ddrb = 0x00 # Data Direction Register B
            self.joystick_state = 0xFF # Bits 0-4 for Joystick 2 (Up, Down, Left, Right, Fire)

        # Timer state
        self.timer_a_latch = 0x0000
        self.timer_b_latch = 0x0000
        self.timer_a_counter = 0x0000
        self.timer_b_counter = 0x0000
        
        # Control Registers
        self.cra = 0x00
        self.crb = 0x00

        # Interrupt Control
        self.icr = 0x00 # Interrupt Control Register (mask)
        self.ifr = 0x00 # Interrupt Flag Register (source)

        self.timer_a_started = False

    def read(self, address):
        """Reads from a CIA register."""
        offset = address & 0x0F # CIA registers are $DC00-$DC0F or $DD00-$DD0F

        if self.is_cia1:
            if offset == 0x00: # PRA (Port A Data Register)
                # This is where the CPU reads the keyboard rows
                # The value written to Port A (self.port_a_output) selects the columns.
                # We need to read the rows based on the selected columns.
                # The keyboard matrix is active low.
                
                # Initialize result with all bits set (no keys pressed)
                result = 0xFF

                # Iterate through each column bit in port_a_output
                for col_idx in range(8):
                    # If the column is selected (bit is 0 in port_a_output)
                    if not ((self.port_a_output >> col_idx) & 1):
                        # OR the row states for this column into the result
                        # If any key in this column is pressed (matrix value is 0),
                        # the corresponding row bit in 'result' should be 0.
                        row_state_for_col = 0xFF
                        for row_idx in range(8):
                            if self.keyboard_matrix[row_idx][col_idx] == 0:
                                row_state_for_col &= ~(1 << row_idx) # Set bit to 0 if key pressed
                        result &= row_state_for_col
                
                # Apply DDR A (Data Direction Register A)
                # Bits set to 0 in DDRA are inputs, so their values come from the keyboard.
                # Bits set to 1 in DDRA are outputs, so their values come from port_a_output.
                # Joystick 2 is also on Port A (first 5 bits). We AND its state.
                final_result = result & self.joystick_state

                return (final_result & ~self.ddra) | (self.port_a_output & self.ddra)


            elif offset == 0x01: # PRB (Port B Data Register)
                # For CIA1, Port B is typically used for joystick input or other I/O.
                # For now, we'll just return its output value.
                return self.port_b_output
            elif offset == 0x02: # DDRA (Data Direction Register A)
                return self.ddra
            elif offset == 0x03: # DDRB (Data Direction Register B)
                return self.ddrb

        # Timer registers (applies to both CIAs)
        if offset == 0x04: # Timer A Low Byte
            return self.timer_a_counter & 0xFF
        elif offset == 0x05: # Timer A High Byte
            return self.timer_a_counter >> 8
        elif offset == 0x06: # Timer B Low Byte
            return self.timer_b_counter & 0xFF
        elif offset == 0x07: # Timer B High Byte
            return self.timer_b_counter >> 8
        elif offset == 0x0D: # ICR (Interrupt Control Register)
            # Reading ICR clears it
            val = self.ifr
            self.ifr = 0
            return val

            # Add other CIA1 registers as needed (timers, interrupt control, etc.)
        
        # Default for other CIAs or unimplemented registers
        # print(f"{self.name} Read from ${address:04X} (Offset: ${offset:02X})")
        return self.registers[offset] # Placeholder

    def write(self, address, data):
        """Writes to a CIA register."""
        offset = address & 0x0F

        if self.is_cia1:
            if offset == 0x00: # ORA (Port A Data Register)
                # This is where the CPU writes to select keyboard columns
                self.port_a_output = data
            elif offset == 0x01: # ORB (Port B Data Register)
                self.port_b_output = data
            elif offset == 0x02: # DDRA (Data Direction Register A)
                self.ddra = data
            elif offset == 0x03: # DDRB (Data Direction Register B)
                self.ddrb = data

        # Timer registers (applies to both CIAs)
        if offset == 0x04: # Timer A Latch Low
            self.timer_a_latch = (self.timer_a_latch & 0xFF00) | data
        elif offset == 0x05: # Timer A Latch High
            self.timer_a_latch = (self.timer_a_latch & 0x00FF) | (data << 8)
            # Writing to high byte of latch also copies latch to counter if timer is stopped
            if not (self.cra & 0b00000001): # If START bit is 0
                self.timer_a_counter = self.timer_a_latch
        elif offset == 0x0E: # CRA (Control Register A)
            self.cra = data
            self.timer_a_started = bool(data & 0b00000001)
        elif offset == 0x0D: # ICR (Interrupt Control Register)
            # Writing to ICR sets/clears bits in the interrupt mask
            if data & 0x80: # Set/Clear bit
                self.icr |= (data & 0x7F)
            else:
                self.icr &= ~(data & 0x7F)
            # Add other CIA1 registers as needed
        
        # Default for other CIAs or unimplemented registers
        # print(f"{self.name} Write to ${address:04X} (Offset: ${offset:02X}) with value ${data:02X}")
        self.registers[offset] = data

    def set_key_state(self, row, col, pressed):
        """Updates the state of a key in the keyboard matrix."""
        if self.is_cia1 and 0 <= row < 8 and 0 <= col < 8:
            self.keyboard_matrix[row][col] = 0 if pressed else 1

    def set_joystick_state(self, direction_bit, pressed):
        """Updates the state of a joystick direction or fire button."""
        if pressed:
            self.joystick_state &= ~(1 << direction_bit) # Clear bit (active low)
        else:
            self.joystick_state |= (1 << direction_bit) # Set bit

    def tick(self):
        """Clock the CIA timers. This should be called once per CPU cycle."""
        # --- Timer A ---
        if self.timer_a_started:
            self.timer_a_counter -= 1
            if self.timer_a_counter < 0:
                # Underflow occurred
                self.ifr |= 0b00000001 # Set Timer A interrupt flag

                # Check if this interrupt is enabled in the mask
                if self.icr & 0b00000001:
                    self.ifr |= 0x80 # Set the main interrupt flag
                    if self.cpu:
                        self.cpu.irq()

                # Check run mode (bit 3 of CRA)
                if self.cra & 0b00001000: # One-shot mode
                    self.timer_a_started = False
                    self.timer_a_counter = self.timer_a_latch # Reload but don't start
                else: # Continuous mode
                    self.timer_a_counter = self.timer_a_latch # Reload and continue

        # --- Timer B ---
        # (Implementation would be very similar to Timer A, using CRB)
        # For now, we focus on Timer A as it's essential for the jiffy interrupt.

    def save_state(self):
        """Saves the CIA's state to a dictionary."""
        # Exclude the CPU reference from being saved
        state = {k: v for k, v in vars(self).items() if k != 'cpu'}
        return state

    def restore_state(self, state):
        """Restores the CIA's state from a dictionary."""
        # The CPU reference is restored separately by the Bus
        for key, value in state.items():
            if key != 'cpu':
                setattr(self, key, value)