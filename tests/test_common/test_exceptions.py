"""
Test FileHarbor Exceptions

Basic tests to validate exception hierarchy and functionality.
"""

import pytest
from fileharbor.common.exceptions import (
    FileHarborException,
    ConnectionError,
    AuthenticationError,
    ChecksumMismatchError,
    PathTraversalError,
    ConfigVersionError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy."""
    
    def test_base_exception(self):
        """Test base FileHarborException."""
        exc = FileHarborException("Test error", details={'key': 'value'})
        assert str(exc) == "Test error (key=value)"
        assert exc.message == "Test error"
        assert exc.details == {'key': 'value'}
    
    def test_connection_error_hierarchy(self):
        """Test connection error is subclass of FileHarborException."""
        exc = ConnectionError("Connection failed")
        assert isinstance(exc, FileHarborException)
        assert isinstance(exc, ConnectionError)
    
    def test_authentication_error_hierarchy(self):
        """Test authentication error hierarchy."""
        exc = AuthenticationError("Auth failed")
        assert isinstance(exc, FileHarborException)
        assert isinstance(exc, ConnectionError)
        assert isinstance(exc, AuthenticationError)


class TestSpecializedExceptions:
    """Test specialized exception classes."""
    
    def test_checksum_mismatch_error(self):
        """Test ChecksumMismatchError with details."""
        exc = ChecksumMismatchError(
            expected="abc123",
            actual="def456",
            filepath="/test/file.txt"
        )
        assert "abc123" in exc.details['expected']
        assert "def456" in exc.details['actual']
        assert exc.details['filepath'] == "/test/file.txt"
    
    def test_path_traversal_error(self):
        """Test PathTraversalError."""
        exc = PathTraversalError("../../etc/passwd")
        assert "../../etc/passwd" in str(exc)
        assert exc.details['attempted_path'] == "../../etc/passwd"
    
    def test_config_version_error(self):
        """Test ConfigVersionError."""
        exc = ConfigVersionError("0.5.0", "1.0.0")
        assert "0.5.0" in str(exc)
        assert "1.0.0" in str(exc)
        assert exc.details['found_version'] == "0.5.0"
        assert exc.details['required_version'] == "1.0.0"


def test_exception_without_details():
    """Test exception creation without details."""
    exc = FileHarborException("Simple error")
    assert str(exc) == "Simple error"
    assert exc.details == {}
