# High-Level Emulation of a Commodore 1541 Disk Drive

class DiskDrive1541:
    """
    A high-level emulation of the 1541 disk drive.
    It parses a .d64 disk image and provides methods to read the directory
    and load files, but does not emulate the drive's own CPU or hardware.
    """
    def __init__(self):
        self.disk_image = None
        self.disk_name = ""
        self.directory = {} # Maps filename to (track, sector)

    def attach_disk_image(self, filename):
        """Loads and parses a .d64 disk image file."""
        try:
            with open(filename, 'rb') as f:
                self.disk_image = list(f.read())
            self._parse_directory()
            print(f"Disk image '{filename}' attached.")
            return True
        except FileNotFoundError:
            print(f"Error: Disk image '{filename}' not found.")
            self.disk_image = None
            return False

    def _get_sector_data(self, track, sector):
        """Reads a 256-byte sector from the disk image."""
        if not self.disk_image:
            return None

        # This is a simplified calculation for sector offset in a .d64 file
        # It assumes a standard 35-track disk image.
        if 1 <= track <= 17:
            offset = (track - 1) * 21
        elif 18 <= track <= 24:
            offset = 17 * 21 + (track - 18) * 19
        elif 25 <= track <= 30:
            offset = 17 * 21 + 7 * 19 + (track - 25) * 18
        else: # 31 <= track <= 35
            offset = 17 * 21 + 7 * 19 + 6 * 18 + (track - 31) * 17
        
        offset += sector
        offset *= 256

        return self.disk_image[offset : offset + 256]

    def _parse_directory(self):
        """Parses the disk directory to find file entries."""
        if not self.disk_image:
            return

        self.directory = {}
        # Directory is always on Track 18
        track = 18
        sector = 1

        # Get disk name from Track 18, Sector 0
        header_sector = self._get_sector_data(18, 0)
        self.disk_name = bytes(b for b in header_sector[144:160] if b != 0xA0).decode('petscii-c64en-lc', errors='ignore').strip()

        while True:
            dir_sector = self._get_sector_data(track, sector)
            if not dir_sector:
                break

            for i in range(0, 256, 32):
                entry = dir_sector[i : i + 32]
                if entry[2] != 0: # File type is not 0 (scratched)
                    file_type = entry[2] & 0x07
                    if file_type == 2: # PRG file type
                        filename_bytes = bytes(b for b in entry[5:21] if b != 0xA0)
                        filename = filename_bytes.decode('petscii-c64en-lc', errors='ignore').strip()
                        file_track = entry[3]
                        file_sector = entry[4]
                        self.directory[filename.upper()] = (file_track, file_sector)

            # Check for next directory sector
            next_track = dir_sector[0]
            next_sector = dir_sector[1]
            if next_track == 0:
                break
            track, sector = next_track, next_sector

    def load_file(self, filename):
        """Loads a file's data from the disk image."""
        filename = filename.upper()
        if filename not in self.directory:
            print(f"File '{filename}' not found on disk.")
            return None

        track, sector = self.directory[filename]
        file_data = []

        while True:
            sector_data = self._get_sector_data(track, sector)
            if not sector_data:
                break
            
            next_track = sector_data[0]
            next_sector = sector_data[1]
            bytes_in_sector = next_sector if next_track != 0 else 256
            file_data.extend(sector_data[2 : bytes_in_sector])

            if next_track == 0:
                break
            track, sector = next_track, next_sector
        
        return file_data

    def _write_sector_data(self, track, sector, data):
        """Writes a 256-byte sector to the disk image."""
        if not self.disk_image or len(data) != 256:
            return

        if 1 <= track <= 17: offset = (track - 1) * 21
        elif 18 <= track <= 24: offset = 17 * 21 + (track - 18) * 19
        elif 25 <= track <= 30: offset = 17 * 21 + 7 * 19 + (track - 25) * 18
        else: offset = 17 * 21 + 7 * 19 + 6 * 18 + (track - 31) * 17
        
        offset += sector
        offset *= 256

        self.disk_image[offset : offset + 256] = data

    def _find_free_sector(self, start_track=1):
        """Finds the first available free sector, starting from a given track."""
        bam_sector = self._get_sector_data(18, 0)
        if not bam_sector: return None, None

        for track in range(start_track, 36):
            # Get the BAM entry for this track
            free_sectors = bam_sector[track * 4]
            if free_sectors > 0:
                # Find the first free sector in this track's bitmap
                bitmap = bam_sector[track * 4 + 1 : track * 4 + 4]
                for sector in range(21): # Max sectors per track
                    byte_idx = sector // 8
                    bit_idx = sector % 8
                    if (bitmap[byte_idx] >> bit_idx) & 1:
                        return track, sector
        return None, None

    def save_file(self, filename, data):
        """Saves a file to the disk image."""
        if not self.disk_image:
            print("No disk image attached to save to.")
            return False

        # 1. Find a free directory entry
        dir_track, dir_sector = 18, 1
        dir_entry_offset = -1
        while True:
            dir_sector_data = self._get_sector_data(dir_track, dir_sector)
            for i in range(0, 256, 32):
                if dir_sector_data[i+2] == 0: # Found a free entry
                    dir_entry_offset = i
                    break
            if dir_entry_offset != -1: break
            dir_track, dir_sector = dir_sector_data[0], dir_sector_data[1]
            if dir_track == 0:
                print("Disk directory is full.")
                return False

        # 2. Find a free sector for the first block of the file
        file_track, file_sector = self._find_free_sector()
        if file_track is None:
            print("Disk is full.")
            return False

        # 3. Create directory entry
        new_entry = bytearray(32)
        new_entry[2] = 0x82 # PRG file type, locked
        new_entry[3], new_entry[4] = file_track, file_sector
        filename_petscii = filename.upper().encode('petscii-c64en-uc', errors='replace')
        new_entry[5:5+len(filename_petscii)] = filename_petscii
        for i in range(5 + len(filename_petscii), 21): new_entry[i] = 0xA0 # Pad with shifted spaces
        # For simplicity, we'll write the directory entry now.
        dir_sector_data[dir_entry_offset:dir_entry_offset+32] = new_entry
        self._write_sector_data(dir_track, dir_sector, dir_sector_data)

        # 4. Write file data, allocating new sectors as needed (simplified)
        # This is a highly simplified implementation that doesn't handle BAM updates
        # or chaining sectors. A full implementation is very complex.
        sector_data = bytearray(256)
        sector_data[0], sector_data[1] = 0, len(data) + 2 # Next T/S (0,0 for last block), bytes used
        sector_data[2:2+len(data)] = data
        self._write_sector_data(file_track, file_sector, sector_data)

        print(f"HLE: Saved '{filename}' to disk (simplified).")
        return True