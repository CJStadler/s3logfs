# FUSE Operations

This doc lists the FUSE operations we will support and describes how they will
work.

See https://github.com/libfuse/libfuse/blob/master/include/fuse_lowlevel.h

- `init()`: Not sure if we need to do anything here, since we also have `__init__`.
- `destroy()`: Unmount.
  1. PUT the current segment to S3.
  2. PUT the checkpoint to S3.
- `lookup(parent_inode_number, name)`: Lookup file/directory by name.
  1. Use imap to get the address of the parent's inode.
  2. Get the block with the parent's inode and deserialize it.
  2. Get the parent's data block(s).
  3. Search the data for `name`, returning the inode number if found.
  4. Use imap to get the address of the inode.
  5. Get the block with the inode and deserialize it.
  6. Return the inode number (and other attributes).
- `forget(inode_number, nlookup)`: Decrement the inode's refcount (stored where?).
  1. ???
  2. If `refcount == 0` then remove the inode's entry in imap?
- `getattr(inode_number)`:
  1. Use imap to get the address of the inode.
  2. Get the block with the inode and deserialize it.
  3. Return the attributes.
- `setattr(inode_number, attr, to_set)`:
  1. Use imap to get the address of the inode.
  2. Get the block with the inode and deserialize it.
  3. For keys in `to_set`, set the inode's attribute to the value in `attr`.
  4. Write the inode to the log.
- `readlink(inode_number)`:
- `mknod(parent_inode_number, name, mode, rdev)`: Create a file with `name`.
  1. Initialize a new INode and set attributes from `mode`.
  2. Write inode to the log.
  3. Add an entry to imap mapping the inode number to its address.
  4. Use imap to get the address of the parent's inode.
  5. Get the block with the parent's inode and deserialize it.
  6. Find a not full data block for the parent directory and add an entry for
    the new file's name and inode number.
  7. Write the parent directory's updated data block to the log and update the
    block's address in the parent directory's inode.
  8. Write the parent directory's inode to the log.
  9. Update the imap with the parent directory inode's new address.
- `mkdir(parent_inode_number, name, mode)`: Create a directory with `name`.
  - Should be similar to `mknod`.
- `unlink(parent_inode_number, name)`: Remove a file from a directory.
  1. Use imap to get address of `parent_inode_number`.
  2. Get the block with the inode and deserialize it.
  3. Find the directory's data block with the file's entry and get the inode number.
  4. Remove the file's entry and write the updated block to the log.
  5. Write the directory inode to the log, with the updated data block address.
  6. Use imap to get the address of the file's inode.
  7. Get the block with the inode and deserialize it.
  8. Decrement the inode's refcount.
  9. If refcount is zero then remove the inode from the imap. Else, write the
    updated inode to the log.
- `rmdir(parent_inode_number, name)`
- `rename(parent_inode_number, name, newparent_inode_number, newname)`
- `link(old_inode_number, newparent_inode_number, newname)`: Create a hard link.
- `open(inode_number)`
- `read(inode_number, size, offset)`
- `write(inode_number, buf, size, offset)`
