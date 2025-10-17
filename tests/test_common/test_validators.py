"""
Test FileHarbor Validators

Tests for path validation and input sanitization.
"""

import pytest
import os
import tempfile
from pathlib import Path

from fileharbor.common.validators import (
    validate_path,
    validate_filename,
    validate_checksum_format,
    validate_port,
    validate_chunk_size,
)
from fileharbor.common.exceptions import (
    PathTraversalError,
    InvalidPathError,
)


class TestPathValidation:
    """Test path validation and traversal prevention."""
    
    def test_valid_path(self):
        """Test validation of a valid path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_path("subdir/file.txt", tmpdir)
            assert result.startswith(tmpdir)
            assert "subdir" in result
            assert "file.txt" in result
    
    def test_path_traversal_prevention(self):
        """Test that path traversal is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(PathTraversalError):
                validate_path("../etc/passwd", tmpdir)
    
    def test_absolute_path_containment(self):
        """Test that absolute paths are contained."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(PathTraversalError):
                validate_path("/etc/passwd", tmpdir)
    
    def test_double_dot_prevention(self):
        """Test prevention of .. in path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(PathTraversalError):
                validate_path("subdir/../../../etc/passwd", tmpdir)
    
    def test_normalized_path_returned(self):
        """Test that normalized path is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_path("./subdir/./file.txt", tmpdir)
            assert "./" not in result
            assert os.path.isabs(result)


class TestFilenameValidation:
    """Test filename validation."""
    
    def test_valid_filename(self):
        """Test validation of valid filename."""
        assert validate_filename("document.txt")
        assert validate_filename("my-file_2024.pdf")
    
    def test_empty_filename(self):
        """Test that empty filename is rejected."""
        with pytest.raises(InvalidPathError):
            validate_filename("")
    
    def test_filename_with_slash(self):
        """Test that filenames with slashes are rejected."""
        with pytest.raises(InvalidPathError):
            validate_filename("subdir/file.txt")
    
    def test_filename_with_backslash(self):
        """Test that filenames with backslashes are rejected."""
        with pytest.raises(InvalidPathError):
            validate_filename("subdir\\file.txt")
    
    def test_reserved_names(self):
        """Test that Windows reserved names are rejected."""
        with pytest.raises(InvalidPathError):
            validate_filename("CON")
        with pytest.raises(InvalidPathError):
            validate_filename("PRN")


class TestChecksumValidation:
    """Test checksum format validation."""
    
    def test_valid_checksum(self):
        """Test validation of valid SHA-256 checksum."""
        valid_checksum = "a" * 64  # 64 hex characters
        assert validate_checksum_format(valid_checksum)
    
    def test_invalid_length(self):
        """Test that invalid length is rejected."""
        with pytest.raises(ValueError):
            validate_checksum_format("abc123")  # Too short
    
    def test_non_hex_characters(self):
        """Test that non-hex characters are rejected."""
        with pytest.raises(ValueError):
            validate_checksum_format("g" * 64)  # 'g' is not hex


class TestPortValidation:
    """Test port number validation."""
    
    def test_valid_port(self):
        """Test validation of valid port numbers."""
        assert validate_port(8443)
        assert validate_port(8080)
        assert validate_port(65535)
    
    def test_invalid_port_low(self):
        """Test that port 0 is rejected."""
        with pytest.raises(ValueError):
            validate_port(0)
    
    def test_invalid_port_high(self):
        """Test that port > 65535 is rejected."""
        with pytest.raises(ValueError):
            validate_port(65536)
    
    def test_non_integer_port(self):
        """Test that non-integer is rejected."""
        with pytest.raises(ValueError):
            validate_port("8443")  # String instead of int


class TestChunkSizeValidation:
    """Test chunk size validation."""
    
    def test_valid_chunk_size(self):
        """Test validation of valid chunk sizes."""
        assert validate_chunk_size(1024 * 1024)  # 1 MB
        assert validate_chunk_size(8 * 1024 * 1024)  # 8 MB
    
    def test_too_small_chunk_size(self):
        """Test that too small chunk size is rejected."""
        with pytest.raises(ValueError):
            validate_chunk_size(1024)  # Less than MIN_CHUNK_SIZE
    
    def test_too_large_chunk_size(self):
        """Test that too large chunk size is rejected."""
        with pytest.raises(ValueError):
            validate_chunk_size(200 * 1024 * 1024)  # Greater than MAX_CHUNK_SIZE
