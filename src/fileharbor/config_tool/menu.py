"""
FileHarbor Interactive Menu System

User-friendly menu interface for configuration management.
"""

import os
import sys
from typing import Optional, Callable, List, Any

from fileharbor.utils import format_file_size


class MenuItem:
    """Represents a menu item."""
    
    def __init__(
        self,
        title: str,
        action: Optional[Callable] = None,
        submenu: Optional['Menu'] = None
    ):
        """
        Initialize menu item.
        
        Args:
            title: Menu item title
            action: Action to execute when selected (optional)
            submenu: Submenu to display when selected (optional)
        """
        self.title = title
        self.action = action
        self.submenu = submenu


class Menu:
    """Interactive menu system."""
    
    def __init__(self, title: str, items: Optional[List[MenuItem]] = None):
        """
        Initialize menu.
        
        Args:
            title: Menu title
            items: List of menu items
        """
        self.title = title
        self.items = items or []
    
    def add_item(self, item: MenuItem) -> None:
        """Add a menu item."""
        self.items.append(item)
    
    def display(self) -> None:
        """Display the menu."""
        self.clear_screen()
        print("=" * 60)
        print(f"  {self.title}")
        print("=" * 60)
        print()
        
        for i, item in enumerate(self.items, 1):
            print(f"  {i}. {item.title}")
        
        print()
    
    def run(self) -> Optional[Any]:
        """
        Run the menu loop.
        
        Returns:
            Result from menu action or None
        """
        while True:
            self.display()
            
            choice = self.prompt_choice(len(self.items))
            
            if choice is None:
                return None  # User wants to go back
            
            item = self.items[choice - 1]
            
            if item.submenu:
                # Display submenu
                result = item.submenu.run()
                if result == 'exit':
                    return 'exit'
            elif item.action:
                # Execute action
                try:
                    result = item.action()
                    if result == 'exit':
                        return 'exit'
                    elif result == 'back':
                        return None
                except KeyboardInterrupt:
                    print("\n\nOperation cancelled.")
                    self.pause()
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    self.pause()
    
    def prompt_choice(self, max_choice: int) -> Optional[int]:
        """
        Prompt user for menu choice.
        
        Args:
            max_choice: Maximum valid choice number
            
        Returns:
            Choice number or None to go back
        """
        while True:
            try:
                choice_str = input(f"Enter choice (1-{max_choice}, or 'b' to go back): ").strip()
                
                if choice_str.lower() in ('b', 'back'):
                    return None
                
                choice = int(choice_str)
                
                if 1 <= choice <= max_choice:
                    return choice
                else:
                    print(f"Please enter a number between 1 and {max_choice}.")
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print()
                return None
    
    @staticmethod
    def clear_screen():
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    @staticmethod
    def pause():
        """Pause and wait for user input."""
        input("\nPress Enter to continue...")
    
    @staticmethod
    def confirm(message: str, default: bool = False) -> bool:
        """
        Prompt user for confirmation.
        
        Args:
            message: Confirmation message
            default: Default value if user just presses Enter
            
        Returns:
            True if confirmed, False otherwise
        """
        default_str = "Y/n" if default else "y/N"
        
        while True:
            response = input(f"{message} [{default_str}]: ").strip().lower()
            
            if not response:
                return default
            
            if response in ('y', 'yes'):
                return True
            elif response in ('n', 'no'):
                return False
            else:
                print("Please enter 'y' or 'n'.")
    
    @staticmethod
    def prompt_string(
        message: str,
        default: Optional[str] = None,
        required: bool = True
    ) -> Optional[str]:
        """
        Prompt user for a string input.
        
        Args:
            message: Prompt message
            default: Default value
            required: Whether input is required
            
        Returns:
            User input or None if cancelled
        """
        if default:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "
        
        while True:
            try:
                value = input(prompt).strip()
                
                if not value and default:
                    return default
                
                if not value and not required:
                    return None
                
                if not value and required:
                    print("This field is required.")
                    continue
                
                return value
            except KeyboardInterrupt:
                print()
                return None
    
    @staticmethod
    def prompt_int(
        message: str,
        default: Optional[int] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Optional[int]:
        """
        Prompt user for an integer input.
        
        Args:
            message: Prompt message
            default: Default value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            User input or None if cancelled
        """
        if default is not None:
            prompt = f"{message} [{default}]: "
        else:
            prompt = f"{message}: "
        
        while True:
            try:
                value_str = input(prompt).strip()
                
                if not value_str and default is not None:
                    return default
                
                if not value_str:
                    print("This field is required.")
                    continue
                
                value = int(value_str)
                
                if min_value is not None and value < min_value:
                    print(f"Value must be >= {min_value}.")
                    continue
                
                if max_value is not None and value > max_value:
                    print(f"Value must be <= {max_value}.")
                    continue
                
                return value
                
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print()
                return None
    
    @staticmethod
    def prompt_choice_from_list(
        message: str,
        choices: List[tuple],
        show_indices: bool = True
    ) -> Optional[int]:
        """
        Prompt user to select from a list.
        
        Args:
            message: Prompt message
            choices: List of (id, display_text) tuples
            show_indices: Whether to show numeric indices
            
        Returns:
            Index of selected choice or None if cancelled
        """
        if not choices:
            print("No options available.")
            Menu.pause()
            return None
        
        print(f"\n{message}")
        print("-" * 60)
        
        for i, (_, display_text) in enumerate(choices, 1):
            if show_indices:
                print(f"  {i}. {display_text}")
            else:
                print(f"  {display_text}")
        
        print()
        
        while True:
            try:
                choice_str = input(f"Enter choice (1-{len(choices)}, or 'c' to cancel): ").strip()
                
                if choice_str.lower() in ('c', 'cancel'):
                    return None
                
                choice = int(choice_str)
                
                if 1 <= choice <= len(choices):
                    return choice - 1
                else:
                    print(f"Please enter a number between 1 and {len(choices)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print()
                return None
    
    @staticmethod
    def display_table(headers: List[str], rows: List[List[str]]) -> None:
        """
        Display a formatted table.
        
        Args:
            headers: Column headers
            rows: Table rows
        """
        if not rows:
            print("No data to display.")
            return
        
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Print headers
        print()
        header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print(header_line)
        print("-" * len(header_line))
        
        # Print rows
        for row in rows:
            row_line = "  ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
            print(row_line)
        
        print()
    
    @staticmethod
    def display_info(label: str, value: Any) -> None:
        """
        Display an information line.
        
        Args:
            label: Information label
            value: Information value
        """
        print(f"  {label}: {value}")
    
    @staticmethod
    def display_header(text: str) -> None:
        """
        Display a section header.
        
        Args:
            text: Header text
        """
        print()
        print("=" * 60)
        print(f"  {text}")
        print("=" * 60)
        print()
    
    @staticmethod
    def display_success(message: str) -> None:
        """Display a success message."""
        print(f"\n✅ {message}")
    
    @staticmethod
    def display_error(message: str) -> None:
        """Display an error message."""
        print(f"\n❌ {message}")
    
    @staticmethod
    def display_warning(message: str) -> None:
        """Display a warning message."""
        print(f"\n⚠️  {message}")
    
    @staticmethod
    def display_info_box(title: str, info: dict) -> None:
        """
        Display information in a formatted box.
        
        Args:
            title: Box title
            info: Dictionary of key-value pairs to display
        """
        print()
        print("=" * 60)
        print(f"  {title}")
        print("=" * 60)
        
        max_key_length = max(len(str(k)) for k in info.keys())
        
        for key, value in info.items():
            # Format value
            if isinstance(value, bool):
                value_str = "Yes" if value else "No"
            elif isinstance(value, int) and value > 1024:
                value_str = f"{value:,} ({format_file_size(value)})"
            else:
                value_str = str(value)
            
            print(f"  {str(key).ljust(max_key_length)} : {value_str}")
        
        print()
