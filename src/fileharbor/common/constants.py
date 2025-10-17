"""
FileHarbor Constants

Global constants and default values used throughout the library.
"""

# ============================================================================
# Version Information
# ============================================================================

PROTOCOL_VERSION = '1.0.0'
CONFIG_VERSION = '1.0.0'

# ============================================================================
# Network Configuration
# ============================================================================

DEFAULT_SERVER_HOST = '0.0.0.0'
DEFAULT_SERVER_PORT = 8443
DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_IDLE_TIMEOUT = 300  # seconds (5 minutes)
DEFAULT_CONNECTION_TIMEOUT = 30  # seconds
DEFAULT_SOCKET_TIMEOUT = 60  # seconds

# ============================================================================
# Transfer Configuration
# ============================================================================

DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
MIN_CHUNK_SIZE = 64 * 1024  # 64 KB
MAX_CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB

DEFAULT_COMPRESSION = False
DEFAULT_VERIFY_CHECKSUMS = True

# ============================================================================
# Threading Configuration
# ============================================================================

DEFAULT_WORKER_THREADS = 4
MIN_WORKER_THREADS = 1
MAX_WORKER_THREADS = 64

# ============================================================================
# Rate Limiting
# ============================================================================

DEFAULT_RATE_LIMIT = 0  # 0 = unlimited (bytes per second)
MIN_RATE_LIMIT = 1024  # 1 KB/s minimum if enabled
RATE_LIMITER_INTERVAL = 0.1  # Check every 100ms

# ============================================================================
# Cryptography
# ============================================================================

# Certificate configuration
CERT_KEY_SIZE = 4096  # RSA key size
CERT_VALIDITY_DAYS = 3650  # 10 years (no expiration management needed)
CERT_HASH_ALGORITHM = 'sha256'

# Encryption configuration
CONFIG_ENCRYPTION_ALGORITHM = 'AES-256-GCM'
KEY_DERIVATION_ITERATIONS = 600000  # PBKDF2 iterations
KEY_DERIVATION_ALGORITHM = 'sha256'
SALT_SIZE = 32  # bytes
NONCE_SIZE = 12  # bytes for AES-GCM
TAG_SIZE = 16  # bytes for AES-GCM

# Checksum algorithm
CHECKSUM_ALGORITHM = 'sha256'
CHECKSUM_BUFFER_SIZE = 65536  # 64 KB for streaming checksum calculation

# ============================================================================
# File Operations
# ============================================================================

# File locking
FILE_LOCK_TIMEOUT = 300  # seconds
FILE_LOCK_CHECK_INTERVAL = 1  # seconds

# Resume information
RESUME_STATE_EXTENSION = '.fharbor_resume'
PARTIAL_FILE_EXTENSION = '.fharbor_partial'

# Metadata
METADATA_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'  # ISO 8601 with microseconds

# ============================================================================
# Logging
# ============================================================================

DEFAULT_LOG_LEVEL = 'INFO'
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

DEFAULT_LOG_FORMAT = (
    '%(asctime)s - %(name)s - %(levelname)s - '
    '%(filename)s:%(lineno)d - %(message)s'
)

DEFAULT_LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Log rotation
DEFAULT_LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
DEFAULT_LOG_BACKUP_COUNT = 5

# ============================================================================
# Protocol Commands
# ============================================================================

# Client to Server commands
CMD_HANDSHAKE = 'HANDSHAKE'
CMD_PUT_START = 'PUT_START'
CMD_PUT_CHUNK = 'PUT_CHUNK'
CMD_PUT_COMPLETE = 'PUT_COMPLETE'
CMD_GET_START = 'GET_START'
CMD_GET_CHUNK = 'GET_CHUNK'
CMD_DELETE = 'DELETE'
CMD_RENAME = 'RENAME'
CMD_MOVE = 'MOVE'
CMD_LIST = 'LIST'
CMD_MKDIR = 'MKDIR'
CMD_RMDIR = 'RMDIR'
CMD_MANIFEST = 'MANIFEST'
CMD_CHECKSUM = 'CHECKSUM'
CMD_STAT = 'STAT'
CMD_EXISTS = 'EXISTS'
CMD_PING = 'PING'
CMD_DISCONNECT = 'DISCONNECT'

# Server to Client responses
RESP_OK = 'OK'
RESP_ERROR = 'ERROR'
RESP_CHUNK_DATA = 'CHUNK_DATA'
RESP_MANIFEST_DATA = 'MANIFEST_DATA'
RESP_LIST_DATA = 'LIST_DATA'
RESP_STAT_DATA = 'STAT_DATA'
RESP_CHECKSUM_DATA = 'CHECKSUM_DATA'

# Status codes
STATUS_SUCCESS = 200
STATUS_PARTIAL_CONTENT = 206
STATUS_BAD_REQUEST = 400
STATUS_UNAUTHORIZED = 401
STATUS_FORBIDDEN = 403
STATUS_NOT_FOUND = 404
STATUS_CONFLICT = 409
STATUS_LOCKED = 423
STATUS_TOO_MANY_REQUESTS = 429
STATUS_INTERNAL_ERROR = 500
STATUS_NOT_IMPLEMENTED = 501
STATUS_SERVICE_UNAVAILABLE = 503
STATUS_INSUFFICIENT_STORAGE = 507

# ============================================================================
# Protocol Message Structure
# ============================================================================

# Message header size (fixed)
MESSAGE_HEADER_SIZE = 1024  # bytes

# Maximum message sizes
MAX_COMMAND_LENGTH = 64
MAX_PATH_LENGTH = 4096
MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # 16 MB
MAX_ERROR_MESSAGE_LENGTH = 1024

# Message encoding
MESSAGE_ENCODING = 'utf-8'

# ============================================================================
# Path Validation
# ============================================================================

# Forbidden path components (prevent traversal)
FORBIDDEN_PATH_COMPONENTS = [
    '..',
    '.',
]

# Forbidden characters in filenames (platform-agnostic)
FORBIDDEN_FILENAME_CHARS = [
    '\x00',  # Null byte
    '/',     # Forward slash (path separator)
    '\\',    # Backslash (Windows path separator)
]

# Maximum path depth
MAX_PATH_DEPTH = 100

# ============================================================================
# Configuration Tool
# ============================================================================

CONFIG_BACKUP_EXTENSION = '.backup'
CONFIG_BACKUP_DATE_FORMAT = '%Y%m%d_%H%M%S'
MAX_CONFIG_BACKUPS = 10

# ============================================================================
# Client Connection Pool
# ============================================================================

DEFAULT_POOL_SIZE = 5
MIN_POOL_SIZE = 1
MAX_POOL_SIZE = 50
POOL_CONNECTION_TIMEOUT = 30  # seconds
POOL_IDLE_TIMEOUT = 300  # seconds

# ============================================================================
# Progress Reporting
# ============================================================================

PROGRESS_UPDATE_INTERVAL = 0.5  # seconds
PROGRESS_RATE_WINDOW = 10  # seconds for rate averaging

# ============================================================================
# Retry Configuration
# ============================================================================

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF_MULTIPLIER = 2.0
MAX_RETRY_DELAY = 60.0  # seconds

# ============================================================================
# File System
# ============================================================================

# Buffer sizes
READ_BUFFER_SIZE = 65536  # 64 KB
WRITE_BUFFER_SIZE = 65536  # 64 KB

# Temporary file prefix
TEMP_FILE_PREFIX = '.fharbor_tmp_'

# ============================================================================
# Session Management
# ============================================================================

SESSION_CLEANUP_INTERVAL = 60  # seconds
SESSION_STATE_FILE = '.fharbor_sessions'

# ============================================================================
# Error Messages
# ============================================================================

ERROR_MSG_INVALID_CONFIG = 'Invalid configuration format'
ERROR_MSG_DECRYPTION_FAILED = 'Failed to decrypt configuration file'
ERROR_MSG_AUTHENTICATION_FAILED = 'Authentication failed'
ERROR_MSG_CERTIFICATE_REVOKED = 'Certificate has been revoked'
ERROR_MSG_PATH_TRAVERSAL = 'Path traversal attempt detected'
ERROR_MSG_LIBRARY_NOT_FOUND = 'Library not found or access denied'
ERROR_MSG_FILE_LOCKED = 'File is locked by another operation'
ERROR_MSG_DISK_FULL = 'Server disk is full'
ERROR_MSG_CHECKSUM_MISMATCH = 'File checksum verification failed'
ERROR_MSG_CONNECTION_LOST = 'Connection to server lost'
ERROR_MSG_TIMEOUT = 'Operation timed out'
ERROR_MSG_RATE_LIMIT = 'Rate limit exceeded'

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_MSG_TRANSFER_COMPLETE = 'Transfer completed successfully'
SUCCESS_MSG_FILE_DELETED = 'File deleted successfully'
SUCCESS_MSG_FILE_RENAMED = 'File renamed successfully'
SUCCESS_MSG_DIRECTORY_CREATED = 'Directory created successfully'
