# Placeholder for the MOS Technology VIC-II (Video Interface Chip)
import pygame

class Sprite:
    """A helper class to manage the state of a single C64 sprite."""
    def __init__(self, sprite_id):
        self.id = sprite_id
        self.x = 0
        self.y = 0
        self.color = 0
        self.enabled = False
        self.expand_y = False
        self.expand_x = False
        self.priority = False # False = Sprite in front, True = Sprite behind background
        self.is_multicolor = False
        self.pointer = 0


class VICII:
    def __init__(self, bus, cpu=None):
        self.bus = bus
        self.cpu = cpu
        # The VIC-II has 64 registers, but many are mirrors.
        # We'll use a 47-byte array for the main registers in the $D000-$D02E range.
        self.registers = [0x00] * 47

        # C64 Screen dimensions
        self.SCREEN_WIDTH_CYCLES = 63 # Cycles per scanline
        self.SCREEN_HEIGHT_RASTER = 312 # Total raster lines for PAL

        # Visible area (approximate for now)
        self.VISIBLE_WIDTH = 320
        self.VISIBLE_HEIGHT = 200
        self.X_SCROLL_OFFSET = 24
        self.Y_SCROLL_OFFSET = 50

        # Internal state
        self.cycle = 0
        self.raster_line = 0

        # Screen buffer
        self.screen_surface = pygame.Surface((self.VISIBLE_WIDTH, self.VISIBLE_HEIGHT))

        # Sprite data
        self.sprites = [Sprite(i) for i in range(8)]
        self.sprite_scanline_buffer = [(0, -1)] * self.VISIBLE_WIDTH # (color_idx, sprite_id)

        # Collision registers (latches)
        self.sprite_sprite_collision = 0x00
        self.sprite_data_collision = 0x00


        # C64 Color Palette (Pepto's palette)
        self.palette = [
            (0, 0, 0), (255, 255, 255), (136, 0, 0), (170, 255, 238),
            (204, 68, 204), (0, 204, 85), (0, 0, 170), (238, 238, 119),
            (221, 136, 85), (102, 68, 0), (255, 119, 119), (51, 51, 51),
            (119, 119, 119), (170, 255, 102), (0, 136, 255), (187, 187, 187)
        ]

        # Character ROM data
        self.char_rom = [0x00] * 0x1000 # 4KB

    def load_char_rom(self, filename="char.rom"):
        """Loads the character ROM."""
        try:
            with open(filename, 'rb') as f:
                self.char_rom = list(f.read(0x1000))
            print(f"Character ROM '{filename}' loaded.")
        except FileNotFoundError:
            print(f"Warning: Character ROM '{filename}' not found. Text will not be rendered correctly.")

    def read(self, address):
        """Reads from a VIC-II register."""
        addr = address & 0x003F
        if addr == 0x11: # Raster line low bits
            return self.raster_line & 0xFF
        if addr == 0x12: # Raster line high bit
            return (self.registers[0x12] & 0x7F) | ((self.raster_line >> 1) & 0x80)
        if addr == 0x1E: # Sprite-Sprite Collision
            val = self.sprite_sprite_collision
            self.sprite_sprite_collision = 0 # Reading clears the register
            return val
        if addr == 0x1F: # Sprite-Data Collision
            val = self.sprite_data_collision
            self.sprite_data_collision = 0 # Reading clears the register
            return val
        if addr == 0x19: # Interrupt Flag Register
            # The top bit is set if any enabled interrupt condition is met
            val = self.registers[0x19]
            if val & self.registers[0x1A]:
                val |= 0x80
            return val
        
        # For other registers, just return the stored value
        if addr < len(self.registers):
            return self.registers[addr]
        return 0

    def write(self, address, data):
        """Writes to a VIC-II register."""
        addr = address & 0x003F
        if addr < len(self.registers):
            self.registers[addr] = data
        
        # Special handling for scroll registers
        # $D011 (Control Register 1) contains vertical scroll (bits 0-2)
        # $D016 (Control Register 2) contains horizontal scroll (bits 0-2)
        
        # Update sprite states based on register writes
        if 0x00 <= addr <= 0x0F: # Sprite X/Y positions
            sprite_id = (addr >> 1)
            if addr & 1: # Y register
                self.sprites[sprite_id].y = data
            else: # X register
                self.sprites[sprite_id].x = data
        elif addr == 0x10: # Sprite X MSB (Most Significant Bit)
            for i in range(8):
                if (data >> i) & 1:
                    self.sprites[i].x |= 0x100
                else:
                    self.sprites[i].x &= 0xFF
        elif addr == 0x15: # Sprite Enable
            for i in range(8):
                self.sprites[i].enabled = bool((data >> i) & 1)
        elif addr == 0x1B: # Sprite Priority (Sprite vs Background)
            for i in range(8):
                self.sprites[i].priority = bool((data >> i) & 1)
        elif addr == 0x17: # Sprite X Expansion
            for i in range(8):
                self.sprites[i].expand_x = bool((data >> i) & 1)
        elif addr == 0x1D: # Sprite Y Expansion
            for i in range(8):
                self.sprites[i].expand_y = bool((data >> i) & 1)
        elif addr == 0x1C: # Sprite Multicolor Mode
            for i in range(8):
                self.sprites[i].is_multicolor = bool((data >> i) & 1)
        elif 0x27 <= addr <= 0x2E: # Sprite colors
            sprite_id = addr - 0x27
            self.sprites[sprite_id].color = data & 0x0F

    def tick(self):
        """Simulates one VIC-II cycle. This should be called for every CPU cycle."""
        # The render_pixel method must be called on every cycle to correctly handle border/screen logic.
        self.render_pixel()

        # Advance raster position
        self.cycle += 1
        if self.cycle >= self.SCREEN_WIDTH_CYCLES:
            self.cycle = 0
            self.raster_line += 1

            # At the start of a new scanline, render all sprites for this line
            self.render_sprites_on_scanline()

            # Check for raster interrupts at the end of the scanline logic
            if self.raster_line == self.registers[0x12] | ((self.registers[0x11] & 0x80) << 1):
                self.trigger_interrupt(0b00000001) # Raster interrupt

            if self.raster_line >= self.SCREEN_HEIGHT_RASTER:
                self.raster_line = 0

    def render_pixel(self):
        """Renders a single pixel to the screen buffer."""
        # Calculate pixel coordinates relative to the visible screen area
        y_screen = self.raster_line - self.Y_SCROLL_OFFSET
        x_screen = self.cycle - self.X_SCROLL_OFFSET

        # If the current raster position is outside the visible 320x200 screen,
        # it's considered the border. We draw the border color and stop.
        if not (0 <= x_screen < self.VISIBLE_WIDTH and 0 <= y_screen < self.VISIBLE_HEIGHT):
            border_color_idx = self.registers[0x20] & 0x0F
            # The screen_surface is 320x200, so we can't draw outside it. This return is correct.
            return

        # --- Get current scroll values ---
        # Horizontal scroll (bits 0-2 of $D016)
        h_scroll = self.registers[0x16] & 0x07
        # Vertical scroll (bits 0-2 of $D011)
        v_scroll = self.registers[0x11] & 0x07

        # Calculate logical pixel coordinates in the C64's memory space, shifted by scroll
        logical_x_pixel = (x_screen + h_scroll) % (40 * 8) # 320 pixels wide
        logical_y_pixel = (y_screen + v_scroll) % (25 * 8) # 200 pixels high

        # --- Determine Background Pixel ---
        background_pixel_is_foreground = False # True if background pixel is a character/bitmap foreground pixel
        bg_color_idx = self.registers[0x21] & 0x0F # Default background color

        # Pointers from VIC register $D018
        vic_mem_pointers = self.registers[0x18]

        # Determine if in bitmap mode (D011, bit 5)
        if self.registers[0x11] & 0x20: # Bitmap Mode (Standard Resolution)
            # Bitmap base address (CB bits 3-1 of D018)
            # This selects one of 8 2KB blocks. The bitmap is 8KB, so it uses 4 consecutive blocks.
            # The actual base address is relative to the VIC's 16KB window.
            # For simplicity, we assume the VIC's 16KB window starts at $0000.
            bitmap_base = ((vic_mem_pointers >> 3) & 0x01) * 0x2000

            # Screen RAM base address (VM bits 7-4 of D018)
            # This selects one of 16 1KB blocks.
            screen_ram_base = ((vic_mem_pointers >> 4) & 0x0F) * 0x400

            # Color RAM is fixed at $D800
            color_ram_base = 0xD800

            # Calculate character cell coordinates
            char_row = logical_y_pixel // 8
            char_col = logical_x_pixel // 8
            y_in_char = logical_y_pixel % 8
            x_in_char = logical_x_pixel % 8

            # Get bitmap data byte
            # Bitmap data is 8 bytes per character row, 40 chars per row, 25 rows.
            bitmap_byte_addr = bitmap_base + (char_row * 40 * 8) + (char_col * 8) + y_in_char
            bitmap_byte = self.bus.read(bitmap_byte_addr)

            # Get color information from Screen RAM and Color RAM
            screen_ram_byte = self.bus.read(screen_ram_base + (char_row * 40) + char_col)
            color_ram_byte = self.bus.read(color_ram_base + (char_row * 40) + char_col)

            fg_color_idx = (screen_ram_byte >> 4) & 0x0F
            bg_color_idx_cell = screen_ram_byte & 0x0F # Background color for this cell

            # Determine pixel color based on bitmap bit
            pixel_bit_set = (bitmap_byte >> (7 - x_in_char)) & 1
            
            if pixel_bit_set:
                final_background_color_idx = fg_color_idx
                background_pixel_is_foreground = True
            else:
                final_background_color_idx = bg_color_idx_cell # Use cell-specific background
                background_pixel_is_foreground = False # It's a background pixel of the cell
        else:
            # Character Mode (existing logic)
            # Which character row and column are we in?
            char_row = logical_y_pixel // 8
            char_col = logical_x_pixel // 8

            # Get screen code from Screen RAM
            screen_ram_base = ((vic_mem_pointers >> 4) & 0x0F) * 0x400
            screen_code_addr = screen_ram_base + (char_row * 40) + char_col
            screen_code = self.bus.read(screen_code_addr)

            # Get character bitmap data from Character ROM
            char_rom_base = ((vic_mem_pointers >> 1) & 0b111) * 0x800 # 2KB blocks
            char_bitmap_addr = (screen_code * 8) + (logical_y_pixel % 8)
            char_bitmap_byte = self.char_rom[char_bitmap_addr]

            # Get color from Color RAM
            color_ram_base = 0xD800
            color_idx = self.bus.read(color_ram_base + (char_row * 40) + char_col) & 0x0F

            # Is the current pixel set in the character bitmap?
            char_pixel_is_set = (char_bitmap_byte >> (7 - (logical_x_pixel % 8))) & 1

            if char_pixel_is_set:
                final_background_color_idx = color_idx
                background_pixel_is_foreground = True
            else:
                final_background_color_idx = bg_color_idx # Use global background color
                background_pixel_is_foreground = False # It's a background pixel of the cell

        # --- Determine Final Pixel Color (Sprite vs Background) ---
        sprite_info = self.sprite_scanline_buffer[x_screen]
        sprite_color_idx = sprite_info[0]
        sprite_id = sprite_info[1]

        final_pixel_color_idx = final_background_color_idx

        if sprite_color_idx != 0 and sprite_id != -1: # A sprite pixel is present
            # Check for sprite-to-data collision before handling priority
            if background_pixel_is_foreground:
                self.sprite_data_collision |= (1 << sprite_id)
                self.trigger_interrupt(0b00000010) # Sprite-Data collision interrupt

            # Now, handle display priority
            sprite_obj = self.sprites[sprite_id]
            if sprite_obj.priority: # Sprite is behind background
                if not background_pixel_is_foreground: # If background is transparent/background color
                    final_pixel_color_idx = sprite_color_idx
            else: # Sprite is in front of background
                final_pixel_color_idx = sprite_color_idx
        
        self.screen_surface.set_at((x_screen, y_screen), self.palette[final_pixel_color_idx])

    def trigger_interrupt(self, flag):
        """Sets an interrupt flag and triggers an IRQ if the mask allows it."""
        self.registers[0x19] |= flag # Set the flag in the interrupt register

        # Check if the corresponding bit in the interrupt mask is also set
        if self.registers[0x1A] & flag:
            if self.cpu:
                self.cpu.irq()

    def render_sprites_on_scanline(self):
        """Pre-renders all visible sprite pixels for the current scanline into a buffer."""
        self.sprite_scanline_buffer = [(0, -1)] * self.VISIBLE_WIDTH # (color_idx, sprite_id)
        
        # Check if current raster line is in the visible Y area
        if not (self.Y_SCROLL_OFFSET <= self.raster_line < self.Y_SCROLL_OFFSET + self.VISIBLE_HEIGHT):
            return

        # Screen RAM location for sprite pointers
        screen_ram_base = ((self.registers[0x18] >> 4) & 0x0F) * 0x400
        sprite_pointer_base = screen_ram_base + 0x03F8

        for sprite in self.sprites: # Iterate from 0 to 7
            if not sprite.enabled:
                continue # Skip disabled sprites

            # Is the sprite visible on this scanline?
            sprite_height = 42 if sprite.expand_y else 21
            if not (sprite.y <= self.raster_line < sprite.y + sprite_height):
                continue

            sprite_row = self.raster_line - sprite.y
            if sprite.expand_y:
                sprite_row //= 2

            # Get sprite data pointer from memory
            sprite.pointer = self.bus.read(sprite_pointer_base + sprite.id)
            sprite_data_addr = sprite.pointer * 64

            # Fetch the 3 bytes for the current sprite row
            row_data_addr = sprite_data_addr + (sprite_row * 3)
            byte1, byte2, byte3 = self.bus.read(row_data_addr), self.bus.read(row_data_addr + 1), self.bus.read(row_data_addr + 2)

            if sprite.is_multicolor:
                # Multicolor mode: 12 double-width pixels, 2 bits per pixel
                mc1 = self.registers[0x25] & 0x0F # Sprite multicolor register 1
                mc2 = self.registers[0x26] & 0x0F # Sprite multicolor register 2

                for i in range(12): # 12 double-width pixels
                    byte_idx = i // 4
                    bit_shift = 6 - (i % 4) * 2
                    color_bits = ((byte1, byte2, byte3)[byte_idx] >> bit_shift) & 0b11

                    if color_bits == 0b00:
                        continue # Transparent

                    pixel_color_idx = 0
                    if color_bits == 0b01:
                        pixel_color_idx = mc1
                    elif color_bits == 0b10:
                        pixel_color_idx = sprite.color
                    elif color_bits == 0b11:
                        pixel_color_idx = mc2

                    pixel_width = 4 if sprite.expand_x else 2
                    pixel_x_start = sprite.x + (i * pixel_width) - self.X_SCROLL_OFFSET

                    for p in range(pixel_width):
                        pixel_x = pixel_x_start + p
                        if 0 <= pixel_x < self.VISIBLE_WIDTH:
                            existing_sprite_id = self.sprite_scanline_buffer[pixel_x][1]
                            if existing_sprite_id != -1:
                                self.sprite_sprite_collision |= (1 << sprite.id) | (1 << existing_sprite_id)
                                self.trigger_interrupt(0b00000100) # Sprite-Sprite collision interrupt
                            # Higher index sprites have priority, so we overwrite
                            self.sprite_scanline_buffer[pixel_x] = (pixel_color_idx, sprite.id)
            else:
                # Single-color mode: 24 single-width pixels, 1 bit per pixel
                for i in range(24):
                    pixel_is_set = ( ( (byte1, byte2, byte3)[i//8] >> (7 - (i%8)) ) & 1 )
                    if pixel_is_set:
                        pixel_width = 2 if sprite.expand_x else 1
                        pixel_x_start = sprite.x + (i * pixel_width) - self.X_SCROLL_OFFSET

                        for p in range(pixel_width):
                            pixel_x = pixel_x_start + p
                            if 0 <= pixel_x < self.VISIBLE_WIDTH:
                                existing_sprite_id = self.sprite_scanline_buffer[pixel_x][1]
                                if existing_sprite_id != -1:
                                    self.sprite_sprite_collision |= (1 << sprite.id) | (1 << existing_sprite_id)
                                    self.trigger_interrupt(0b00000100) # Sprite-Sprite collision interrupt
                                # Higher index sprites have priority, so we overwrite
                                self.sprite_scanline_buffer[pixel_x] = (sprite.color, sprite.id)

    def get_screen_surface(self):
        """Returns the current screen buffer as a Pygame Surface."""
        return self.screen_surface

    def is_badline(self):
        """
        Determines if the current raster_line is a "badline".
        A badline occurs when the VIC-II needs to fetch graphics data,
        halting the CPU for approximately 40 cycles.
        """
        # Badlines only occur when the display is enabled (DEN bit in $D011 is 1)
        display_enabled = self.registers[0x11] & 0x10

        # And only within the visible screen area (roughly)
        is_visible_scanline = 50 <= self.raster_line < 250

        if not display_enabled or not is_visible_scanline:
            return False

        # The primary condition for a badline is that the VIC-II is about to
        # fetch a new row of character/bitmap data. This happens every 8 scanlines,
        # but is shifted by the vertical scroll value.
        v_scroll = self.registers[0x11] & 0x07
        if (self.raster_line & 0x07) == v_scroll:
            return True

        # The second condition is if a sprite's DMA is activated.
        # This happens when the raster line matches the Y-coordinate of an enabled sprite.
        for sprite in self.sprites:
            if sprite.enabled and sprite.y == self.raster_line:
                return True

        return False

    def get_cycles_stolen(self):
         #This function is returning the number of cycle that would be substracted from the CPU every `badline`.
         return 40

    def save_state(self):
        """Saves the VIC-II's state to a dictionary."""
        sprite_states = [vars(s) for s in self.sprites]
        return {
            'registers': self.registers,
            'cycle': self.cycle,
            'raster_line': self.raster_line,
            'sprite_sprite_collision': self.sprite_sprite_collision,
            'sprite_data_collision': self.sprite_data_collision,
            'sprites': sprite_states
        }

    def restore_state(self, state):
        """Restores the VIC-II's state from a dictionary."""
        self.registers = state['registers']
        self.cycle = state['cycle']
        self.raster_line = state['raster_line']
        self.sprite_sprite_collision = state['sprite_sprite_collision']
        self.sprite_data_collision = state['sprite_data_collision']
        
        sprite_states = state['sprites']
        for i in range(8):
            # Re-create sprite objects from saved state
            s_state = sprite_states[i]
            self.sprites[i] = Sprite(s_state['id'])
            for key, value in s_state.items():
                setattr(self.sprites[i], key, value)