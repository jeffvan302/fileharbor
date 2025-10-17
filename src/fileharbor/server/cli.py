"""
FileHarbor Server CLI

Command-line interface for starting the FileHarbor server.

Usage:
    fileharbor-server <config_file> [--password PASSWORD]
"""

import sys
import argparse
from pathlib import Path

from fileharbor.__version__ import __version__
from fileharbor.common.exceptions import (
    FileHarborException,
    ConfigurationError,
    ServerStartupError,
)
from fileharbor.server.config import load_server_config
from fileharbor.server.server import FileHarborServer


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='FileHarbor Server - Secure file transfer server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server with plain config
  fileharbor-server server_config.json

  # Start server with encrypted config
  fileharbor-server server_config.json.encrypted --password mypassword

  # Start server (password will be prompted)
  fileharbor-server server_config.json.encrypted

For more information, visit: https://github.com/yourusername/fileharbor
        """
    )
    
    parser.add_argument(
        'config',
        type=str,
        help='Path to server configuration file'
    )
    
    parser.add_argument(
        '--password',
        type=str,
        default=None,
        help='Password for encrypted configuration (will prompt if not provided)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'FileHarbor Server v{__version__}'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for server CLI."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Display banner
        print()
        print("=" * 60)
        print(f"  FileHarbor Server v{__version__}")
        print("  Secure File Transfer with mTLS")
        print("=" * 60)
        print()
        
        # Load configuration
        print(f"📂 Loading configuration: {args.config}")
        config = load_server_config(args.config, password=args.password)
        print(f"✅ Configuration loaded successfully")
        print()
        
        # Create and start server
        server = FileHarborServer(config)
        server.start()
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    
    except FileNotFoundError as e:
        print(f"\n❌ Error: Configuration file not found")
        print(f"   {e}")
        sys.exit(1)
    
    except ConfigurationError as e:
        print(f"\n❌ Configuration Error:")
        print(f"   {e}")
        print()
        print("💡 Tip: Use 'fileharbor-config' to create or edit configuration")
        sys.exit(1)
    
    except ServerStartupError as e:
        print(f"\n❌ Server Startup Error:")
        print(f"   {e}")
        sys.exit(1)
    
    except FileHarborException as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected Error:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
