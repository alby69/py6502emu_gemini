# MOS Technology 6581 SID (Sound Interface Device) Emulator
import numpy as np

# These tables determine how many clock cycles are needed for the envelope counter to change.
# Derived from SID analysis (e.g., reSID). The rates are for the PAL C64 clock (~985248 Hz).
ATTACK_RATES = [2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000]
DECAY_RELEASE_RATES = [6, 24, 48, 72, 114, 168, 204, 240, 300, 750, 1500, 2400, 3000, 9000, 15000, 24000]

# A lookup table to simulate the exponential decay curve.
EXPONENTIAL_DECAY = [1, 30, 30, 30, 30, 30, 30, 16, 16, 16, 16, 16, 16, 16, 16, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

class Voice:
    """Represents a single voice of the SID chip."""
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.clock_rate = 985248 # PAL clock
        self.phase_accumulator = 0
        self.noise_shift_register = 0x7FFFFF

        # Registers
        self.freq = 0
        self.pulse_width = 0
        self.control = 0
        self.attack_decay = 0
        self.sustain_release = 0

        # Envelope state
        self.rate_counter = 0
        self.envelope_state = 'RELEASE' # ATTACK, DECAY, SUSTAIN, RELEASE
        self.envelope_counter = 0 # 8-bit counter

    def update_envelope(self):
        gate = self.control & 0x01

        if gate:
            if self.envelope_state == 'RELEASE':
                self.envelope_state = 'ATTACK'
        else:
            self.envelope_state = 'RELEASE'

        attack_rate_idx = self.attack_decay >> 4
        decay_rate_idx = self.attack_decay & 0x0F
        sustain_level = (self.sustain_release >> 4) / 15.0
        sustain_level_int = (self.sustain_release & 0xF0) | (self.sustain_release >> 4)
        release_rate_idx = self.sustain_release & 0x0F

        if self.envelope_state == 'ATTACK':
            # The famous ADSR bug: if the attack rate is high enough, the counter
            # can wrap around past 0xFF and get stuck at a high value.
            step = EXPONENTIAL_DECAY[self.envelope_counter ^ 0xFF]
            if self.envelope_counter + step >= 0xFF:
                self.envelope_counter = 0xFF
                self.envelope_state = 'DECAY'
            else:
                self.envelope_counter += step

        elif self.envelope_state == 'DECAY':
            if self.envelope_counter != sustain_level_int:
                self.envelope_counter -= 1
            if self.envelope_counter <= sustain_level_int:
                self.envelope_counter = sustain_level_int
                self.envelope_state = 'SUSTAIN'

        elif self.envelope_state == 'SUSTAIN':
            if self.envelope_counter != sustain_level_int:
                self.envelope_counter -= 1 # Continue decay if sustain is lowered

        elif self.envelope_state == 'RELEASE':
            self.envelope_counter -= 1

        if self.envelope_counter < 0:
            self.envelope_counter = 0

    def generate_sample(self):
        # The envelope counter is the primary volume control
        envelope_volume = self.envelope_counter / 255.0

        if envelope_volume == 0.0:
            return 0.0

        waveform_type = self.control & 0xF0
        output = 0.0

        # Triangle Wave
        if waveform_type & 0x10:
            # Simple triangle wave generation
            output = 2.0 * (self.phase_accumulator / 0xFFFFFF) - 1.0
            output = abs(output) * 2.0 - 1.0 # Invert the top half

        # Sawtooth Wave
        elif waveform_type & 0x20:
            output = 2.0 * (self.phase_accumulator / 0xFFFFFF) - 1.0

        # Noise waveform uses the same output as sawtooth, but the phase is reset pseudo-randomly.
        elif waveform_type & 0x80:
            # The output is the high byte of the phase accumulator
            output = 2.0 * (self.phase_accumulator / 0xFFFFFF) - 1.0

        # Pulse Wave
        elif waveform_type & 0x40:
            pulse_compare = self.pulse_width << 12
            output = 1.0 if self.phase_accumulator < pulse_compare else -1.0

        # Advance phase accumulator based on frequency
        # The constant is approximately (PAL_CLOCK_FREQ / 2^24)
        phase_step = int(self.freq * 16.777216 / self.clock_rate)
        old_phase = self.phase_accumulator
        self.phase_accumulator = (self.phase_accumulator + phase_step) & 0xFFFFFF

        # If noise waveform is selected, clock the noise register when the phase accumulator wraps.
        if waveform_type & 0x80 and self.phase_accumulator < old_phase:
            # 23-bit LFSR with taps at bits 22 and 17
            new_bit = ((self.noise_shift_register >> 22) ^ (self.noise_shift_register >> 17)) & 1
            self.noise_shift_register = ((self.noise_shift_register << 1) | new_bit) & 0x7FFFFF
            # Reset phase accumulator with the noise value
            self.phase_accumulator = self.noise_shift_register << 1

        return output * envelope_volume

    def tick(self):
        """Clock the envelope generator. Called once per sample."""
        self.rate_counter -= self.clock_rate / self.sample_rate
        if self.rate_counter <= 0:
            rate_index = 0
            if self.envelope_state == 'ATTACK':
                rate_index = self.attack_decay >> 4
                self.rate_counter += ATTACK_RATES[rate_index]
            elif self.envelope_state == 'DECAY':
                rate_index = self.attack_decay & 0x0F
                self.rate_counter += DECAY_RELEASE_RATES[rate_index]
            elif self.envelope_state == 'RELEASE':
                rate_index = self.sustain_release & 0x0F
                self.rate_counter += DECAY_RELEASE_RATES[rate_index]
            else: # Sustain
                self.rate_counter = 0xFFFF # Effectively pause counter

            self.update_envelope()



class SID:
    def __init__(self):
        self.registers = [0x00] * 32
        self.sample_rate = 44100 # Samples per second

        self.voices = [Voice(self.sample_rate) for _ in range(3)]

        # Master volume
        self.volume = 0.0

        # External audio input
        self.external_in = 0.0

        # Filter state
        self.filter_cutoff = 0
        self.filter_resonance = 0
        self.filter_route = 0 # Bitmask for voices
        self.filter_mode = 0 # Low, Band, High pass modes
        self.voice3_off = False

        # Internal filter state variables
        self.low_pass_output = 0.0
        self.band_pass_output = 0.0

    def read(self, address):
        """Reads from a SID register."""
        offset = address & 0x1F # SID registers are in a 32-byte range

        if offset == 0x1B: # OSC3 - Read Voice 3 Oscillator
            # The top 8 bits of the voice's phase accumulator
            return self.voices[2].phase_accumulator >> 16
        if offset == 0x1C: # ENV3 - Read Voice 3 Envelope
            return self.voices[2].envelope_counter

        return self.registers[offset]

    def write(self, address, data):
        """Writes to a SID register."""
        offset = address & 0x1F
        self.registers[offset] = data

        # Route write to the correct voice or global register
        if 0x00 <= offset <= 0x06:
            self.update_voice_register(self.voices[0], offset, data)
        elif 0x07 <= offset <= 0x0D:
            self.update_voice_register(self.voices[1], offset - 0x07, data)
        elif 0x0E <= offset <= 0x14:
            self.update_voice_register(self.voices[2], offset - 0x0E, data)
        elif offset == 0x15: # Filter Cutoff Low
            self.filter_cutoff = (self.filter_cutoff & 0x07F8) | (data & 0x07)
        elif offset == 0x16: # Filter Cutoff High
            self.filter_cutoff = (self.filter_cutoff & 0x0007) | (data << 3)
        elif offset == 0x17: # Resonance and Filter Routing
            self.filter_resonance = (data >> 4) / 15.0 # Normalize to 0.0-1.0
            self.filter_route = data & 0x0F
        elif offset == 0x18: # Volume and Filter settings
            self.volume = (data & 0x0F) / 15.0
            self.filter_mode = data & 0x70
            self.voice3_off = bool(data & 0x80)





    def update_voice_register(self, voice, reg, data):
        """Updates a register within a specific voice."""
        if reg == 0: # Freq Low
            voice.freq = (voice.freq & 0xFF00) | data
        elif reg == 1: # Freq High
            voice.freq = (voice.freq & 0x00FF) | (data << 8)
        elif reg == 2: # Pulse Low
            voice.pulse_width = (voice.pulse_width & 0x0F00) | data
        elif reg == 3: # Pulse High
            voice.pulse_width = (voice.pulse_width & 0x00FF) | ((data & 0x0F) << 8)
        elif reg == 4: # Control Register
            voice.control = data
        elif reg == 5: # Attack/Decay
            voice.attack_decay = data
        elif reg == 6: # Sustain/Release
            voice.sustain_release = data

    def generate_audio_buffer(self, length):
        """Generates a buffer of audio samples."""
        buffer = np.zeros(length, dtype=np.int16)
        max_amplitude = 32767 * self.volume / 3.0 # Divide by 3 to prevent clipping

        # Calculate filter coefficients once per buffer
        # This is an approximation. A real SID's cutoff is not linear.
        cutoff_w = 2.0 * np.pi * (self.filter_cutoff / 2047.0) * 11000.0 / self.sample_rate
        f = 2.0 * np.sin(cutoff_w / 2.0)
        q = 1.0 - self.filter_resonance

        for i in range(length):
            for voice in self.voices:
                voice.tick()

            # Determine input to the filter
            filter_input = 0.0
            v_outs = [v.generate_sample() for v in self.voices]
            if self.voice3_off: v_outs[2] = 0.0

            for i, v_out in enumerate(v_outs):
                if self.filter_route & (1 << i):
                    filter_input += v_out

            # Digital State-Variable Filter algorithm
            self.low_pass_output += f * self.band_pass_output
            high_pass_output = filter_input - self.low_pass_output - q * self.band_pass_output
            self.band_pass_output += f * high_pass_output

            # Select filtered output based on mode
            filtered_output = 0.0
            if self.filter_mode & 0x10: # Low-pass
                filtered_output += self.low_pass_output
            elif self.filter_mode & 0x20: # Band-pass
                filtered_output += self.band_pass_output
            elif self.filter_mode & 0x40: # High-pass
                filtered_output += high_pass_output

            # Mix final output
            final_mix = filtered_output
            for i, v_out in enumerate(v_outs):
                if not (self.filter_route & (1 << i)):
                    final_mix += v_out
            
            # Add external audio input to the final mix
            final_mix += self.external_in

            # Clamp and convert to 16-bit integer
            final_sample = np.clip(final_mix * max_amplitude, -32768, 32767)
            buffer[i] = int(final_sample)

        return buffer

    def save_state(self):
        """Saves the SID's state to a dictionary."""
        voice_states = [vars(v) for v in self.voices]
        return {
            'registers': self.registers,
            'volume': self.volume,
            'external_in': self.external_in,
            'filter_cutoff': self.filter_cutoff,
            'filter_resonance': self.filter_resonance,
            'filter_route': self.filter_route,
            'filter_mode': self.filter_mode,
            'voice3_off': self.voice3_off,
            'low_pass_output': self.low_pass_output,
            'band_pass_output': self.band_pass_output,
            'voices': voice_states
        }

    def restore_state(self, state):
        """Restores the SID's state from a dictionary."""
        for key, value in state.items():
            if key != 'voices':
                setattr(self, key, value)
        
        voice_states = state['voices']
        for i in range(3):
            for key, value in voice_states[i].items():
                setattr(self.voices[i], key, value)