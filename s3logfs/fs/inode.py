from struct import Struct
from array import array
from .blockaddress import BlockAddress

class INode:
    NUMBER_OF_BLOCKS = 16
    STRUCT_FORMAT = 'ILI????LLL' # Plus block addresses
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
        self.block_addresses = self.NUMBER_OF_BLOCKS * [BlockAddress(0, 0)]

    @classmethod
    def from_bytes(klass, bytes):
        struct_bytes = bytes[:klass.STRUCT.size]
        addresses_bytes = bytes[klass.STRUCT.size:]
        unpacked_values = klass.STRUCT.unpack(struct_bytes)

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
            inode.status_last_changed_at
        ) = unpacked_values

        address_size = len(addresses_bytes) // klass.NUMBER_OF_BLOCKS
        for i in range(klass.NUMBER_OF_BLOCKS):
            offset = i * address_size
            address_bytes = addresses_bytes[offset:offset + address_size]
            inode.block_addresses[i] = BlockAddress(address_bytes)

        return inode

    def to_bytes(self):
        struct_bytes = self.STRUCT.pack(
            self.inode_number,
            self.size,
            self.hard_links,
            self.is_directory,
            self.readable,
            self.writable,
            self.executable,
            self.last_accessed_at,
            self.last_modified_at,
            self.status_last_changed_at
        )

        bytes = bytearray(struct_bytes)

        for i in range(self.NUMBER_OF_BLOCKS):
            address = self.block_addresses[i]
            bytes.extend(address.to_bytes())

        return bytes
