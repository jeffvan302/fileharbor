# FileHarbor Windows Quick Reference Card

## 🚀 First-Time Setup

```cmd
# 1. Run automated setup
setup_windows.bat

# 2. Activate environment (if not already active)
conda activate fileharbor

# 3. Open in VS Code
code .
```

---

## 🔄 Daily Workflow

```cmd
# Activate environment
conda activate fileharbor

# Open VS Code
code .

# Run tests
test.bat

# Start server
fileharbor-server server_config.json
```

---

## 🧪 Testing Commands

```cmd
test.bat                    # All tests
test.bat integration       # Integration tests
test.bat security          # Security tests
test.bat e2e              # End-to-end tests
test.bat coverage         # With coverage report
```

---

## 🎮 VS Code Shortcuts

### General
- `Ctrl+Shift+P` - Command palette
- `Ctrl+P` - Quick open file
- `Ctrl+`` ` - Toggle terminal
- `Ctrl+B` - Toggle sidebar
- `Ctrl+Shift+F` - Search in files

### Editing
- `Shift+Alt+F` - Format document
- `Ctrl+/` - Toggle comment
- `Alt+Up/Down` - Move line up/down
- `Ctrl+D` - Select next occurrence
- `Ctrl+Shift+L` - Select all occurrences

### Debugging
- `F5` - Start/continue debugging
- `F9` - Toggle breakpoint
- `F10` - Step over
- `F11` - Step into
- `Shift+F11` - Step out
- `Shift+F5` - Stop debugging

### Testing
- Click flask icon → Test Explorer
- Right-click test → Run/Debug
- `Ctrl+Shift+P` → "Test: Run All Tests"

---

## 🔧 Common Commands

```cmd
# Install/Update
pip install -e .
conda env update -f environment.yml --prune

# Format code
black src/ tests/

# Lint
flake8 src/ tests/ --max-line-length=120

# Type check
mypy src/fileharbor

# Run FileHarbor
fileharbor-server server_config.json
fileharbor-config server_config.json

# Examples
python examples\sync_client_example.py
python examples\async_client_example.py
```

---

## 🐛 Debug Configurations (F5)

1. **Python: Current File** - Debug open file
2. **FileHarbor: Start Server** - Debug server
3. **FileHarbor: Config Tool** - Debug config tool
4. **FileHarbor: Sync Client Example** - Debug sync example
5. **FileHarbor: Async Client Example** - Debug async example
6. **Python: Debug Tests** - Debug test file
7. **Python: All Tests** - Debug all tests

---

## 📁 Important Files

```
fileharbor/
├── environment.yml          # Conda environment
├── setup_windows.bat        # Setup script
├── test.bat                 # Test runner
├── WINDOWS_SETUP.md         # Full guide
├── .vscode/                 # VS Code config
│   ├── settings.json        # Editor settings
│   ├── launch.json          # Debug configs
│   └── tasks.json           # Tasks
├── src/fileharbor/          # Source code
├── tests/                   # Tests
└── examples/                # Examples
```

---

## 🚨 Troubleshooting

### Conda not found
```cmd
# Restart terminal after installing Miniconda
# Or add to PATH: C:\Users\YourName\miniconda3\Scripts
```

### Command not found
```cmd
conda activate fileharbor
pip install -e .
```

### Port already in use
```cmd
netstat -ano | findstr :8443
taskkill /PID <PID> /F
```

### Import errors
```cmd
pip install -e .
# Or restart VS Code
```

---

## 📊 VS Code Tasks (Ctrl+Shift+P → Tasks: Run Task)

- Install Package (Development Mode)
- Run All Tests
- Run Integration Tests
- Run Security Tests
- Run E2E Tests
- Run Tests with Coverage
- Format Code (Black)
- Sort Imports (isort)
- Lint (Flake8)
- Type Check (mypy)
- Clean Build Artifacts
- Start FileHarbor Server
- Open Config Tool
- Run Sync Client Example
- Run Async Client Example

---

## 💡 Pro Tips

1. **Auto-format on save** - Already configured!
2. **Multiple terminals** - Click + in terminal panel
3. **Split editor** - `Ctrl+\`
4. **Zen mode** - `Ctrl+K Z` (distraction-free)
5. **Command palette** - `Ctrl+Shift+P` for everything
6. **Go to definition** - `F12` or `Ctrl+Click`
7. **Find references** - `Shift+F12`
8. **Rename symbol** - `F2`

---

## 📚 Resources

- `WINDOWS_SETUP.md` - Complete setup guide
- `README.md` - Project overview
- `CLIENT_QUICK_START.md` - Client usage
- `COMPLETION.md` - Feature list
- Hover over functions for documentation
- `Ctrl+Click` to jump to definition

---

## 🎯 Getting Started Checklist

- [ ] Install Miniconda
- [ ] Run `setup_windows.bat`
- [ ] Open in VS Code: `code .`
- [ ] Select Python interpreter (fileharbor)
- [ ] Install recommended extensions
- [ ] Run tests: `test.bat`
- [ ] Create config: `fileharbor-config server_config.json`
- [ ] Start coding!

---

**For full details, see WINDOWS_SETUP.md**

**Happy coding! 🚀**
