from .blockaddress import BlockAddress
from array import array

class AddressBlock:

    # init AddressBlock with byte data, address_size
    def __init__(self, address_block, address_size):
        self.data = address_block
        self.address_size = address_size

    def get_address(self, offset):
        start = offset * address_size
        end = start + address_size
        address = BlockAddress(self.data[start:end])
        return address

    def set_address(self, offset, address):
        start = offset * address_size
        end = start + address_size
        self.data = self.data[:start] + address.to_bytes() + self.data[end:]

    def get_max_offset(self):
        return len(self.data) // address_size

    def to_bytes():
        return self.data
