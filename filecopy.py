#!/usr/bin/env python

"""
Modern file copy for Linux 2.6.32+.
"""

import os
import errno
import fcntl
import ctypes
import logging
import ctypes.util

try:
    # local module
    import splice
except AttributeError:
    splice = None

logger = logging.getLogger(__file__)

BTRFS_IOCTL_MAGIC = 0x94
F_SETPIPE_SZ = 1031

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14  # arch-specific
_IOC_DIRBITS = 2  # arch-specific
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = (_IOC_NRSHIFT + _IOC_NRBITS)
_IOC_SIZESHIFT = (_IOC_TYPESHIFT + _IOC_TYPEBITS)
_IOC_DIRSHIFT = (_IOC_SIZESHIFT + _IOC_SIZEBITS)
_IOC_WRITE = 1

try:
    # use system maximum pipe buffer size as chunksize
    with open('/proc/sys/fs/pipe-max-size', 'r') as fp:
        CHUNKSIZE = int(fp.read())
    del fp
    logger.debug('Using chunksize (from pipe-max-size) %d', CHUNKSIZE)
except IOError:
    CHUNKSIZE = 8 * 64 * 1024


libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
try:
    sendfile = libc.sendfile
    c_loff_t = ctypes.c_uint64
    c_loff_t_p = ctypes.POINTER(c_loff_t)
    sendfile.argtypes = [ctypes.c_int, ctypes.c_int, c_loff_t_p, ctypes.c_size_t]
    sendfile.restype = ctypes.c_ssize_t
except AttributeError:
    sendfile = None


def reflink_fps(source_fp, dest_fp):
    """Use btrfs-specific reflink ioctl to link two file contents together."""
    # BTRFS_IOC_CLONE _IOW (BTRFS_IOCTL_MAGIC, 9, int)
    sizeof_int = 4
    ioctl_number = (_IOC_WRITE << _IOC_DIRSHIFT) | \
                   (BTRFS_IOCTL_MAGIC << _IOC_TYPESHIFT) | \
                   (9 << _IOC_NRSHIFT) | \
                   (sizeof_int << _IOC_SIZESHIFT)

    try:
        fcntl.ioctl(dest_fp.fileno(), ioctl_number, source_fp.fileno())
    except IOError as ex:
        msg = 'btrfs reflink failed: %s' % ex.strerror
        raise NotImplementedError(msg)


def splice_fps(source_fp, dest_fp):
    if not splice:
        raise NotImplementedError('No splice() implementation')

    logger.debug('Using splice_fps to copy file data')
    pipe_r, pipe_w = os.pipe()
    try:
        fcntl.fcntl(pipe_w, F_SETPIPE_SZ, CHUNKSIZE)
    except IOError:
        logger.debug('Failed to expand pipe buffer to chunksize %d', CHUNKSIZE)

    try:
        while True:
            # splice into kernel memory
            buffered = splice.splice(source_fp.fileno(), None, pipe_w, None, CHUNKSIZE,
                                     splice.SPLICE_F_MOVE | splice.SPLICE_F_MORE)
            if buffered == 0:
                break  # done
            # splice into dest file
            while buffered > 0:
                ret = splice.splice(pipe_r, None, dest_fp.fileno(), None, buffered,
                                    splice.SPLICE_F_MOVE | splice.SPLICE_F_MORE)
                if ret > 0:
                    buffered -= ret
    except IOError as e:
        if e.errno in (errno.EBADF, errno.EINVAL):
            raise NotImplementedError('Unsupported splice() implementation')


def sendfile_fps(source_fp, dest_fp):
    if not sendfile:
        raise NotImplementedError('No sendfile() implementation')

    logger.debug('Using sendfile_fps to copy file data')
    offset = ctypes.c_uint64(0)
    while True:
        ret = sendfile(dest_fp.fileno(), source_fp.fileno(), offset, CHUNKSIZE)
        if ret == 0:
            # done
            return
        elif ret == -1:
            errno_ = ctypes.get_errno()
            if errno_ in (errno.EBADF, errno.EFAULT, errno.EINVAL):
                raise NotImplementedError('Unsupported sendfile() implementation')
            raise IOError(errno_, os.strerror(errno_))
        elif ret < 0:
            raise IOError('sendfile failed with %d' % ret)


def readwrite_fds(source_fp, dest_fp):
    logger.debug('Using readwrite_fds to copy file data')
    buf = None
    while buf != '':
        buf = source_fp.read(CHUNKSIZE)
        dest_fp.write(buf)


def copy_data(source_fp, dest_fp):
    """Copy contents from source_fp to dest_fp. If splice is available, use that.
    Otherwise falls back to read/write loop."""

    source_pos = source_fp.tell()
    dest_pos = dest_fp.tell()

    for copy_fn in (reflink_fps, sendfile_fps, splice_fps, readwrite_fds):
        try:
            copy_fn(source_fp, dest_fp)
            return
        except NotImplementedError:
            source_fp.seek(source_pos, os.SEEK_SET)
            dest_fp.seek(dest_pos, os.SEEK_SET)
            continue

    raise NotImplementedError('No copy_fn works on this platform')
