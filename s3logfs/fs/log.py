from collections import defaultdict
from .segment import ReadOnlySegment, ReadWriteSegment
from .blockaddress import BlockAddress

class Log:
    """
    Abstract representation of the log.

    Only a single instance of this class should exist for a filesystem at one
    time.
    """
    # default value for blocksize for tests
    BLOCK_SIZE = 4096

    def __init__(self, next_segment_number, bucket, block_size=4096, max_segment_count=512):

        # file system details
        self._block_size = block_size
        self._max_segment_count = max_segment_count
        self._bucket = bucket

        # BCH - removed to switch to defaultdict data structure
        # self._current_segment = ReadWriteSegment()
        # self.last_segment_number = last_segment_number

        # init empty dict for segments
        self._segments = defaultdict()

        # create current segment and add to segments
        self._current_segment_id = next_segment_number
        self._segments[self._current_segment_id] = ReadWriteSegment(self._current_segment_id, 
                                                                    self._block_size, 
                                                                    self._max_segment_count)
        # going to buffer ahead the next segment ahead of time, so that 
        # transitioning from one write buffer to the next is fast
        self._segments[self._current_segment_id+1] = ReadWriteSegment(self._current_segment_id+1,
                                                                      self._block_size,
                                                                      self._max_segment_count)

    def get_current_segment_id(self):
        return self._current_segment_id

    def get_block_size(self):
        return self._block_size

    def get_max_segment_count(self):
        return self._max_segment_count - 1
    
    def read(self, block_address):
        try:
          # return block of data if in memory
          return self._segments[block_address.segmentid].read(block_address.offset)
        except:
          # load segment into memory from S3 and return block of data
          seg_bytes = self._bucket.get_segment(block_address.segmentid)
          self._segments[block_address.segmentid] = ReadOnlySegment(block_address.segmentid, 
                                                                    self._block_size, 
                                                                    self._max_segment_count, 
                                                                    seg_bytes)
          return self._segments[block_address.segmentid].read(block_address.offset)

          # NOTE: the above method of loading the segment, and then returning the block
          # would be expensive, at least in the overall delay to the running program
          # I would adjust this to start a thread which would load the segment 
          # from S3 into the segments dict, and then just grab the block from S3 and
          # return it. The thread would populate the data into the segments dict
          # for future reads in parallel

    def write(self, block_bytes):

        # write data and get block number
        block_number = self._segments[self._current_segment_id].write(block_bytes)

        # create BlockAddress
        block_address = BlockAddress(self._current_segment_id, block_number)

        # verify if segment is full
        if (self._segments[self._current_segment_id].is_full()):

          # last segment
          last_segment_id = self._current_segment_id

          # if full, transition to new write buffer (should be pre-defined)
          self._current_segment_id += 1

          # transition previous segment to read-only
          self._segments[last_segment_id] = self._segments[last_segment_id].to_read_only()

          # create the next write buffer (pre paring for future use)
          self._segments[self._current_segment_id+1] = ReadWriteSegment(self._current_segment_id+1,
                                                                        self._block_size,
                                                                        self._max_segment_count)


        # return BlockAddress for segment/block_number
        return block_address
