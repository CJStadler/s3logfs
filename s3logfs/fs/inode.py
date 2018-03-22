from struct import Struct
from array import array


class INode:
    NUMBER_OF_BLOCKS = 16
    STRUCT_FORMAT = 'ILI????LLL{}L{}H'.format(
        NUMBER_OF_BLOCKS, NUMBER_OF_BLOCKS)
    STRUCT = Struct(STRUCT_FORMAT)

    def __init__(self):
        self.inode_number = 0
        self.size = 0
        self.hard_links = 0
        self.is_directory = False
        self.readable = False
        self.writable = False
        self.executable = False
        self.last_accessed_at = 0
        self.last_modified_at = 0
        self.status_last_changed_at = 0
        self.block_addresses = self.NUMBER_OF_BLOCKS * [(0, 0)]

    @classmethod
    def from_bytes(klass, bytes):
        unpacked_values = klass.STRUCT.unpack(bytes)

        segment_and_block_numbers = klass.NUMBER_OF_BLOCKS * 2 * [0]
        inode = klass()
        (
            inode.inode_number,
            inode.size,
            inode.hard_links,
            inode.is_directory,
            inode.readable,
            inode.writable,
            inode.executable,
            inode.last_accessed_at,
            inode.last_modified_at,
            inode.status_last_changed_at,
            *segment_and_block_numbers
        ) = unpacked_values

        for i in range(klass.NUMBER_OF_BLOCKS):
            segment_number = segment_and_block_numbers[i]
            block_number = segment_and_block_numbers[klass.NUMBER_OF_BLOCKS + i]
            inode.block_addresses[i] = (segment_number, block_number)

        return inode

    def to_bytes(self):
        segment_and_block_numbers = self.NUMBER_OF_BLOCKS * 2 * [0]

        for i in range(self.NUMBER_OF_BLOCKS):
            (segment_number, block_number) = self.block_addresses[i]
            segment_and_block_numbers[i] = segment_number
            segment_and_block_numbers[self.NUMBER_OF_BLOCKS + i] = block_number

        return self.STRUCT.pack(
            self.inode_number,
            self.size,
            self.hard_links,
            self.is_directory,
            self.readable,
            self.writable,
            self.executable,
            self.last_accessed_at,
            self.last_modified_at,
            self.status_last_changed_at,
            *segment_and_block_numbers
        )
