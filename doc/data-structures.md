# Overview
Most of the notes about data structures below is based on "The Design and Implementation of a Log-Structured File System" paper by Rosenblum/Ousterhout. It is based on a Log-Structured FS called Sprite LFS. I have/will review a few other implementations and make notes below as to how they differ. Added some design information from a Harvard presentation http://www.eecs.harvard.edu/~cs161/notes/lfs.pdf. University of Wisconsin resource: http://pages.cs.wisc.edu/~remzi/Classes/537/Fall2008/Notes/file-lfs.txt

Superblock (fixed location - not part of log structure)
----------------------
This is likely still needed to define the type and size of our file system for the OS (and likely FUSE) to make use of. This should be stored in the S3 bucket as a data structure. Technically, we could just combine the Superblock into the CheckpointRegion.

CheckpointRegion (fixed location - not part of log structure)
----------------------
The CheckpointRegion data structure will hold the the inode to imap relationship. So each file would have a unique Inode value, that will never change, but the Inode's address can change as new versions of it are written to the log file structure. Each time a new Inode is written a new imap object is also written. The imap's unique ID never changes, but the address pointer to the most recent Inode is updated, as well as the verison of the imap if the file is truncated/deleted.

Inode ID (file id) > Imap Object > Inode Address in Storage

So the CheckpointRegion will have an index of all Inode to all most recent Imap Objects in memory.

The CheckpointRegion (in RAM) is the current state of the file sytsem, though it may not reflect all data on disk as it will also represent information in the write buffer. 

On some set schedule, or when a specific amount of data has been writen to the file system, the CheckpointRegion will need to be written to storage as a checkpoint. All data from before the checkpoint should be considered fully committed to memory, and after a re-mount or crash recovery we should be able to load the CheckpointRecovery from disk to memroy, then read ahead in the log (FS) and update the CR structure to reflect writes that were successful to disk, and remove elements from the file system that did not complete, then mount the file system for use.

Sprite LFS uses a 30 seconds till Checkpoint process.

InodeMap
----------------------
The InodeMap will contain the the segment & offset to the current Inode for a file. It will maintain a version number to reflect if the Inode has been deleted/truncated for cleanup detection. It could also contain the current segment & offset for the Directory inode entry for the file.

```
InodeMap
  - InodeID
  - IMapBlockAddress
```
INodeMap now becomes a woring index to both the directory lookup, and data lookup for a file.

Inode
----------------------
The Inode will represent a file, and all of its required data points for tracking the status and use of the file and its data.

Elements such as type, owner, permissions, date created/modified, direct/indirect data block addresses as well as a number of other fields. To flesh this out we will want to review the current Inode structure in common FS used in linux, to make sure we support most file system functionality, as well ad make adjustments to support the type of file system we are implementing.

BlockAddress
----------------------
The BlockAddress structure is how we will store addresses. When the data is in S3, the structure is going to be an integer for the Segment and an integer for the offset in the segment to the data block. When we start talking about cache, we could have an array of Segments in memory, we would use the block address data to scan the in memory array for a Segment first, if it is not found (miss) we then go to S3, load it into memory, then read the data from there.

```
BlockAddress
  - SegmentID (6 byte unsigned long long)
  - Offset (2 byte unsigned short)
```

IndirectBlock
----------------------
The IndirectBlock is an array of segment and offset addresses to data blocks which will fully contain pointers to other data blocks. Each Inode will have a number of direct data block addresses, but once those are exceeded it will transition into IndirectBlocks to extend the file system. 

I think we should also include in this data structure a level, which will represent how many levels we will need to go to get to actual data blocks. So if it says 2, then it would be Inode > IndirectBlockAddress > IndirectBlockAddress > DataAddress. This way the data structure can be reused for multiple layers as needed.

```
IndirectBlock
  - level
  - array of DataBlock addresses (order in array defines order in memory)
```
level will let the class know how deep it will need to go to get to actual data, and how to calculate which branch to go down 
in the addresses to get to it. 

Segment
----------------------
The Segment data structure will be an array of byte blocks of page size (ex: 4096). The first (offset 0) will be the SegmentSummary which will detail all of the data blocks in the Segment like a table of contents, and provide information on how to find them and validate they are live. See SegmentSummary data structure.

```
Segment
  - SegmentSummary
  - N Blocks (data, inode, imap, etc) until we fill the needed segment size
```
Sprite LFS uses 512K or 1MB segments per the paper.

SegmentSummary
----------------------
The SegmentSummary will be used by the garbage collection and cleanup processes to determine if a data block is still live within a segment. Generally located in the first block, or offset 0 of each segment.

The Sprite LFS implementation stores the following for each data block in the segment ...
- file id (aka inode id)
- imap version (incremented value, only incremented when a file is deleted and/or truncated)
- offset in segment to data block

The file id combined with the imap version represent a unique ID, if these values do not match the current inode/imap version in the CheckpointRecovery structure the data block is considered junk an can be deleted. If we decide to implement versioning, we can then use a date/time stamp and age to determine when we remove blocks.

Harvard LFS Materials shows a slightly different implementation ...
 - file id (inode id)
 - offset in segment

It then determines live blocks of data by using the inode number to read the current inode via the inodemap. It then checks if it is the same block adresss. With our implementation this would be as simple as checking if the segment id in the inode we read matches the segment id for the segment we are going through the segment summary to detect bad blocks. If the segment ID is different, then the inodemap brought us to a newer segment for the given data block.

Sprite LFS also has a SegmentUsageTable, as a method by which to identify Segments that can be cleaned. The usage table keeps track of the number of live blocks in a given segment and the most recent modified time. Sprite LFS has this data structure as separate from the SegmentSummary data structure but I believe they can be combined.

```
SegmentSummary
  - number of live blocks
  - last modified of any data block (3 inodes in segment, greatest last modified from these files)
  - array of SSData elements stored in their offset position
  - Note: data block at offset 10, is in array position 10

SSData
  - file number
  - imap version
  - last modified
```
