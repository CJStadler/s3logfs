from .blockaddress import BlockAddress
from array import array

class AddressBlock:

    # init AddressBlock with byte data, address_size
    def __init__(self, address_block):
        self.data = address_block
        self.address_size = BlockAddress.get_address_size()

    def get_address(self, offset):
        start = offset * self.address_size
        end = start + self.address_size
        addr_data = bytearray()
        addr_data.extend(self.data[start:end])
        address = BlockAddress(addr_data)
        return address

    def set_address(self, address, offset):
        start = offset * self.address_size
        end = start + self.address_size
        self.data = self.data[:start] + address.to_bytes() + self.data[end:]

    def get_max_offset(self):
        return len(self.data) // self.address_size

    def count(self):
        return len(self.data) // self.address_size

    def get_bytes(self):
        return bytes(self.data)
