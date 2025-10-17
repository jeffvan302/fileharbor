"""
FileHarbor Compression Utilities

Optional compression support for file transfers.
"""

import zlib
from typing import bytes as Bytes


# Compression level (0-9, where 9 is maximum compression)
DEFAULT_COMPRESSION_LEVEL = 6


def compress_data(data: Bytes, level: int = DEFAULT_COMPRESSION_LEVEL) -> Bytes:
    """
    Compress data using zlib.
    
    Args:
        data: Data to compress
        level: Compression level (0-9)
        
    Returns:
        Compressed data
    """
    return zlib.compress(data, level=level)


def decompress_data(compressed_data: Bytes) -> Bytes:
    """
    Decompress zlib-compressed data.
    
    Args:
        compressed_data: Compressed data
        
    Returns:
        Decompressed data
        
    Raises:
        zlib.error: If decompression fails
    """
    return zlib.decompress(compressed_data)


class CompressedStream:
    """
    Streaming compression wrapper.
    
    Allows compressing data in chunks for large files.
    """
    
    def __init__(self, level: int = DEFAULT_COMPRESSION_LEVEL):
        """
        Initialize compressed stream.
        
        Args:
            level: Compression level (0-9)
        """
        self.compressor = zlib.compressobj(level=level)
        self._finalized = False
    
    def compress(self, data: Bytes) -> Bytes:
        """
        Compress a chunk of data.
        
        Args:
            data: Data chunk to compress
            
        Returns:
            Compressed data chunk
        """
        if self._finalized:
            raise ValueError("Stream has been finalized")
        return self.compressor.compress(data)
    
    def finalize(self) -> Bytes:
        """
        Finalize compression and get remaining data.
        
        Returns:
            Final compressed data chunk
        """
        if self._finalized:
            return b''
        self._finalized = True
        return self.compressor.flush()


class DecompressedStream:
    """
    Streaming decompression wrapper.
    
    Allows decompressing data in chunks for large files.
    """
    
    def __init__(self):
        """Initialize decompressed stream."""
        self.decompressor = zlib.decompressobj()
        self._finalized = False
    
    def decompress(self, data: Bytes) -> Bytes:
        """
        Decompress a chunk of data.
        
        Args:
            data: Compressed data chunk
            
        Returns:
            Decompressed data chunk
        """
        if self._finalized:
            raise ValueError("Stream has been finalized")
        return self.decompressor.decompress(data)
    
    def finalize(self) -> Bytes:
        """
        Finalize decompression and get remaining data.
        
        Returns:
            Final decompressed data chunk
        """
        if self._finalized:
            return b''
        self._finalized = True
        return self.decompressor.flush()


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio.
    
    Args:
        original_size: Original size in bytes
        compressed_size: Compressed size in bytes
        
    Returns:
        Compression ratio (e.g., 0.5 means 50% of original size)
    """
    if original_size == 0:
        return 0.0
    return compressed_size / original_size


def is_compression_beneficial(original_size: int, compressed_size: int) -> bool:
    """
    Determine if compression is beneficial.
    
    Compression is considered beneficial if it reduces size by at least 10%.
    
    Args:
        original_size: Original size in bytes
        compressed_size: Compressed size in bytes
        
    Returns:
        True if compression is beneficial
    """
    return calculate_compression_ratio(original_size, compressed_size) < 0.9
