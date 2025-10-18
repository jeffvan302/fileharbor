"""
FileHarbor Server CLI

Command-line interface for starting the FileHarbor server.

Usage:
    fileharbor-server <config_file> [--password PASSWORD]
"""

import sys
import argparse
import threading
import platform
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


def monitor_keyboard(server: FileHarborServer, stop_event: threading.Event):
    """
    Monitor keyboard input for graceful shutdown.
    
    Args:
        server: FileHarborServer instance to stop
        stop_event: Event to signal when monitoring should stop
    """
    try:
        system = platform.system()
        
        if system == 'Windows':
            import msvcrt
            while not stop_event.is_set() and server.running:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Check for 'q', 'Q', or ESC (ASCII 27)
                    if key in (b'q', b'Q', b'\x1b'):
                        print("\n\n🛑 Shutdown requested...")
                        server.stop()
                        break
                stop_event.wait(0.1)
        else:
            # Unix/Linux/Mac
            import termios
            import tty
            
            # Save terminal settings
            stdin_fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(stdin_fd)
            
            try:
                # Set terminal to raw mode for immediate key detection
                tty.setcbreak(stdin_fd)
                
                while not stop_event.is_set() and server.running:
                    # Check if input is available (non-blocking)
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        # Check for 'q', 'Q', or ESC
                        if key.lower() == 'q' or ord(key) == 27:
                            print("\n\n🛑 Shutdown requested...")
                            server.stop()
                            break
            finally:
                # Restore terminal settings
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)
                
    except Exception as e:
        # Silently handle any keyboard monitoring errors
        pass


def main():
    """Main entry point for server CLI."""
    server = None
    keyboard_thread = None
    stop_event = threading.Event()
    
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
        
        # Create server
        server = FileHarborServer(config)
        
        # Start keyboard monitoring thread
        keyboard_thread = threading.Thread(
            target=monitor_keyboard,
            args=(server, stop_event),
            daemon=True,
            name="KeyboardMonitor"
        )
        keyboard_thread.start()
        
        # Display exit instructions
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║  Press 'Q' or 'ESC' to gracefully shutdown the server    ║")
        print("║  Or use Ctrl+C for immediate shutdown                    ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        
        # Start server (this blocks)
        server.start()
        
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user (Ctrl+C)")
        if server:
            server.stop()
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
    
    finally:
        # Signal keyboard thread to stop
        stop_event.set()
        if keyboard_thread and keyboard_thread.is_alive():
            keyboard_thread.join(timeout=1.0)


if __name__ == '__main__':
    main()
