from .blockaddress import BlockAddress
from .log import Log
from struct import *
from array import array
from errno import ENOENT
from stat import *
from time import time
from collections import *

class INode:
    NUMBER_OF_DIRECT_BLOCKS = 16
    STRUCT_FORMAT = 'QQQQIIIIIddd' # Plus block addresses
    STRUCT = Struct(STRUCT_FORMAT)

    def __init__(self):
        # unique inode id
        self.inode_number = 0
        # parent inode id, to make it easier to implement ".."
        self.parent = 0
        # size of data (all 3 used by FUSE)
        self.size = 0                     # st_size - total bytes (file data, or pathname size for link)
        self.block_count = 0              # st_blocks - number of blocks (usually in 512-byte units)
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
        now = time()
        self.last_accessed_at = now       # st_atime
        self.last_modified_at = now       # st_mtime
        self.status_last_changed_at = now # st_ctime
        self.block_offset = 0
        self.block_addresses = self.NUMBER_OF_DIRECT_BLOCKS * [BlockAddress()]
        # for directory lookups, will be populated from data after inode is loaded
        self.children = {}

    @classmethod
    def from_bytes(klass, data):
        # trim off padding (anything inluding or after \x3C "<")
#        bytes = data[0:data.index(b'\x3C')]
        # pull data out of block of bytes
        struct_bytes = data[:klass.STRUCT.size]
        addresses_bytes = data[klass.STRUCT.size:]
        unpacked_values = klass.STRUCT.unpack(struct_bytes)

        # pattern: QQQQIIIIIddd
        inode = klass()
        (
            inode.inode_number,
            inode.parent,
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
        # pattern: QQQQIIIIIddd
        struct_bytes = self.STRUCT.pack(
            self.inode_number,
            self.parent,
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

        # end data with "<"
        data.extend(b'\x3C')

        return bytes(data)

    # returns True if iNode is a directory
    def is_directory(self):
        return (S_ISDIR(self.mode) != 0)

    # returns True if iNode is a regular file
    def is_file(self):
        return (S_ISREG(self.mode) != 0)

    # returns True if iNode is a symbolic link
    def is_symlink(self):
        return (S_ISLNK(self.mode) != 0)

    # returns the file type portion of mode
    def get_type(self):
        return S_IFMT(self.mode)

    # set type
    def set_type(self, inode_type):
        self.mode = (self.mode ^ S_IFMT(self.mode)) | inode_ntype

    # returns an attr dict object for inode, used by FUSE
    def get_attr(self):
        attr = dict(
                 st_ino=self.inode_number,
                 st_mode=self.mode,
                 st_size=self.size,
                 st_blocks=self.block_count,
                 st_blksize=self.block_size,
                 st_nlink=self.hard_links,
                 st_uid=self.uid,
                 st_gid=self.gid,
                 st_atime=self.last_accessed_at,
                 st_mtime=self.last_modified_at,
                 st_ctime=self.status_last_changed_at)
        return attr

    # permission check
    #
    #          READ     WRITE    EXECUTE
    #   Owner  S_IRUSR  S_IWUSR  S_IXUSR
    #   Group  S_IRGRP  S_IWGRP  S_IXGRP
    #   Other  S_IROTH  S_IWOTH  S_IXOTH
    #
    # EX: check if owner has read permissions
    #     has_permission(S_IRUSR)
    def has_permission(self, perm):
        if (perm >=1 and perm <= 4):
            return (self.mode & S_IRWXO & perm > 0)
        elif (perm >= 8 and perm <= 32):
            return (self.mode & S_IRWXG & perm > 0)
        else:
            return (self.mode & S_IRWXU & perm > 0)

    # check if a given chmod value matches the current value
    def chmod_match(self, chmod):
        return (((self.mode & S_IRWXU) | (self.mode & S_IRWXG) | (self.mode & S_IRWXO)) == chmod)

    def set_chmod(self, chmod):
        self.mode = (self.mode ^ S_IMODE(self.mode)) | chmod

    def get_chmod(self):
        return S_IMODE(self.mode)

    # this method allows us to set the address at the next block_offset
    # NOTE: needs to be extended with indirect pointers
    def write_address(self, address, offset=''):
        if (offset==''):
            if (self.block_offset < self.NUMBER_OF_DIRECT_BLOCKS):
                self.block_addresses[self.block_offset] = address
                self.block_offset += 1
            else:
                # INDIRECT BLOCKS
                return NotImplemented
        else:
            if (offset < self.NUMBER_OF_DIRECT_BLOCKS):
                self.block_addresses[offset] = address
                self.block_offset = offset + 1
            else:
                # INDIRECT BLOCKS
                return NotImplemented

        # increase block_count if we just wrote an address to a higher 
        if (self.block_count < self.block_offset):
            self.block_count = self.block_offset

    # this method allows us to read the address at the next block_offset
    # NOTE: needs to be extended with indirect pointers
    def read_address(self, offset=''):
        if (offset==''):
            if (self.block_offset < self.NUMBER_OF_DIRECT_BLOCKS):
                address = self.block_addresses[self.block_offset]
                self.block_offset += 1
                return address
            else:
                # INDIRECT BLOCKS
                return NotImplemented
        else:
            if (offset < self.NUMBER_OF_DIRECT_BLOCKS):
                address = self.block_addresses[offset]
                self.block_offset = offset + 1
                return address
            else:
                # INDIRECT BLOCKS
                return NotImplemented

    # this will convert the children entries to bytes
    def children_to_bytes(self):
        # get number of children
        child_count = len(self.children)
        # define bytearray
        child_data = bytearray()
        # add child count to bytearray
        child_data.extend(pack("I", child_count))
        # loop thruogh children and append their data line by line
        for key, value in self.children.items():
            line = str(key) + "|" + str(value) + "\n"
            child_data.extend(line.encode('utf-8'))
        # terminate data with an left arrow (<) which should not exist in this data
        child_data.extend(b'\x3C')
        return bytes(child_data)

    # this will convert the byte data to children entries
    def bytes_to_children(self, data):
        count = unpack("I",data[0:4])[0]
        data = data[4:data.index(b'\x3C')]
        for line in data.splitlines():
            child_data = line.decode().split("|")
            self.children[child_data[0]] = child_data[1]
