from .blockaddress import BlockAddress
from struct import Struct
from array import array
from errno import ENOENT
from stat import *
from time import time

class INode:
    NUMBER_OF_DIRECT_BLOCKS = 16
    STRUCT_FORMAT = 'QQQIIIIILLL' # Plus block addresses
    STRUCT = Struct(STRUCT_FORMAT)

    def __init__(self):
        # unique inode id
        self.inode_number = 0
        # size of data (all 3 used by FUSE)
        self.size = 0                     # st_size - total bytes (file data, or pathname size for link)
        self.block_count = 0              # st_blocks - number of blocks (usually in 512-byte units, not blksize)
        self.block_size = 0               # st_blksize
        # st_mode (file type + permissions combined via masking)
        #   S_IFMT     0o170000   bit mask for the file type bit field
        #   S_IFSOCK   0o140000   socket
        #   S_IFLINK   0o120000   symbolic link
        #   S_IFREG    0o100000   regular file
        #   S_IFBLK    0o060000   block device
        #   S_IFDIR    0o040000   directory
        #   S_IFCHR    0o020000   character device
        #   S_IFIFO    0o010000   FIFO
        #   perm       0o000XXX   permissions = O|G|U w/ value  0 to 7
        self.mode = 0         
        # owner and group id's
        self.uid = 0                      # st_uid
        self.gid = 0                      # st_gid
        # number of sub-directories in a directory includnig "." and ".."
        self.hard_links = 0               # st_nlink
        # file accessed timestamps
        self.last_accessed_at = 0         # st_atime
        self.last_modified_at = 0         # st_mtime
        self.status_last_changed_at = 0   # st_ctime
        self.block_addresses = self.NUMBER_OF_DIRECT_BLOCKS * [BlockAddress()]

    @classmethod
    def from_bytes(klass, bytes):
        struct_bytes = bytes[:klass.STRUCT.size]
        addresses_bytes = bytes[klass.STRUCT.size:]
        unpacked_values = klass.STRUCT.unpack(struct_bytes)

        inode = klass()
        (
            inode.inode_number,
            inode.size,
            inode.block_count,
            inode.block_size,    
            inode.mode,         
            inode.uid,
            inode.gid,
            inode.hard_links,
            inode.last_accessed_at,
            inode.last_modified_at,
            inode.status_last_changed_at
        ) = unpacked_values

        address_size = len(addresses_bytes) // klass.NUMBER_OF_DIRECT_BLOCKS
        for i in range(klass.NUMBER_OF_DIRECT_BLOCKS):
            offset = i * address_size
            address_bytes = addresses_bytes[offset:offset + address_size]
            inode.block_addresses[i] = BlockAddress(address_bytes)

        return inode

    def to_bytes(self):
        struct_bytes = self.STRUCT.pack(
            self.inode_number,
            self.size,
            self.block_count,
            self.block_size,    
            self.mode,         
            self.uid,
            self.gid,
            self.hard_links,
            self.last_accessed_at,
            self.last_modified_at,
            self.status_last_changed_at
        )

        data = bytearray(struct_bytes)

        for i in range(self.NUMBER_OF_DIRECT_BLOCKS):
            address = self.block_addresses[i]
            data.extend(address.to_bytes())

        return data

    # returns True if iNode is a directory
    def is_directory(self):
        return (S_ISDIR(self.mode) != 0)

    # returns True if iNode is a regular file
    def is_file(self):
        return (S_ISREG(self.mode) != 0)

    # returns True if iNode is a symbolic link
    def is_link(self):
        return (S_ISLNK(self.mode) != 0)
