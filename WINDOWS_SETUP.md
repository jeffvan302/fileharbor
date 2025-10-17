# FileHarbor Windows Development Guide

Complete guide for developing and testing FileHarbor on Windows with Miniconda and VS Code.

---

## 📋 Prerequisites

### Required Software

1. **Miniconda** (or Anaconda)
   - Download: https://docs.conda.io/en/latest/miniconda.html
   - Choose Python 3.13 version for Windows
   - During installation, check "Add to PATH" option

2. **Visual Studio Code**
   - Download: https://code.visualstudio.com/
   - Install with default settings

3. **Git for Windows** (optional but recommended)
   - Download: https://git-scm.com/download/win
   - Use default settings

---

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

1. Open PowerShell or Command Prompt
2. Navigate to the project directory:
   ```cmd
   cd C:\path\to\fileharbor
   ```

3. Run the setup script:
   ```cmd
   setup_windows.bat
   ```

This will:
- Create conda environment
- Install all dependencies
- Install FileHarbor in development mode
- Set up everything automatically

### Option 2: Manual Setup

1. **Create Conda Environment:**
   ```cmd
   conda env create -f environment.yml
   ```

2. **Activate Environment:**
   ```cmd
   conda activate fileharbor
   ```

3. **Install FileHarbor:**
   ```cmd
   pip install -e .
   ```

---

## 💻 VS Code Setup

### 1. Open Project in VS Code

```cmd
cd C:\path\to\fileharbor
code .
```

### 2. Install Recommended Extensions

When you open the project, VS Code will prompt you to install recommended extensions. Click **"Install All"**.

Key extensions:
- Python (Microsoft)
- Pylance
- Black Formatter
- isort
- Flake8
- Mypy Type Checker

### 3. Select Python Interpreter

1. Press `Ctrl+Shift+P`
2. Type: "Python: Select Interpreter"
3. Choose: `Python 3.13.x ('fileharbor')`
   - Look for the one that includes your conda environment path

### 4. Verify Setup

Open VS Code terminal (`` Ctrl+` ``) and verify:
```cmd
python --version
# Should show: Python 3.13.x

conda env list
# Should show 'fileharbor' environment active

pip list | findstr fileharbor
# Should show: fileharbor (development mode)
```

---

## 🧪 Running Tests

### Using Batch File (Easy)

```cmd
# All tests
test.bat

# Specific test suites
test.bat integration
test.bat security
test.bat e2e

# With coverage
test.bat coverage
```

### Using Python Script

```cmd
# All tests
python run_tests.py

# Specific suites
python run_tests.py integration
python run_tests.py security
python run_tests.py e2e
```

### Using Pytest Directly

```cmd
# All tests
pytest -v

# Specific test file
pytest tests/test_integration/test_server_client.py -v

# Specific test
pytest tests/test_integration/test_server_client.py::TestIntegration::test_upload_download -v

# With coverage
pytest --cov=fileharbor --cov-report=html
```

### In VS Code

#### Method 1: Test Explorer
1. Click the Testing icon in the sidebar (flask icon)
2. Click "Refresh Tests"
3. Click ▶ to run individual tests or entire suites

#### Method 2: Debug Tests
1. Open test file
2. Set breakpoints
3. Press `F5` and select "Python: Debug Tests"

#### Method 3: Tasks
1. Press `Ctrl+Shift+P`
2. Type: "Tasks: Run Task"
3. Select test task (e.g., "Run All Tests")

---

## 🏃 Running FileHarbor

### Start Server

**Option 1: Command Line**
```cmd
fileharbor-server server_config.json
```

**Option 2: VS Code Debug**
1. Press `F5`
2. Select "FileHarbor: Start Server"

**Option 3: VS Code Task**
1. Press `Ctrl+Shift+P`
2. "Tasks: Run Task" → "Start FileHarbor Server"

### Configuration Tool

**Option 1: Command Line**
```cmd
fileharbor-config server_config.json
```

**Option 2: VS Code Debug**
1. Press `F5`
2. Select "FileHarbor: Config Tool"

### Run Examples

**Sync Client:**
```cmd
python examples/sync_client_example.py
```

**Async Client:**
```cmd
python examples/async_client_example.py
```

**Debug Examples:**
1. Open example file
2. Press `F5`
3. Select "Python: Current File"

---

## 🔧 Development Workflow

### Typical Development Cycle

1. **Activate Environment:**
   ```cmd
   conda activate fileharbor
   ```

2. **Open in VS Code:**
   ```cmd
   code .
   ```

3. **Make Changes:**
   - Edit code in `src/fileharbor/`
   - Changes are immediately available (development mode)

4. **Run Tests:**
   ```cmd
   test.bat
   ```

5. **Debug if Needed:**
   - Set breakpoints in VS Code
   - Press `F5` and select appropriate debug configuration

6. **Format Code:**
   - Automatic on save (if configured)
   - Or press `Shift+Alt+F`
   - Or run: `black src/ tests/`

---

## 🐛 Debugging Tips

### Setting Breakpoints

1. Click in the gutter (left of line numbers)
2. Red dot appears = breakpoint set
3. Press `F5` to start debugging
4. Execution pauses at breakpoints

### Debug Configurations Available

- **Python: Current File** - Debug currently open file
- **FileHarbor: Start Server** - Debug server
- **FileHarbor: Config Tool** - Debug config tool
- **FileHarbor: Sync Client Example** - Debug sync example
- **FileHarbor: Async Client Example** - Debug async example
- **Python: Debug Tests** - Debug test file
- **Python: All Tests** - Debug all tests

### Debug Console

When paused at a breakpoint:
- Type variable names to inspect values
- Execute Python code
- Call functions

### Common Debug Shortcuts

- `F5` - Start debugging
- `F9` - Toggle breakpoint
- `F10` - Step over
- `F11` - Step into
- `Shift+F11` - Step out
- `F5` - Continue
- `Shift+F5` - Stop debugging

---

## 📝 Code Quality Tools

### Auto-Format on Save

VS Code is configured to:
- Auto-format with Black on save
- Auto-organize imports with isort on save

### Manual Formatting

```cmd
# Format all code
black src/ tests/ examples/

# Sort imports
isort src/ tests/ examples/

# Lint
flake8 src/ tests/ examples/ --max-line-length=120

# Type check
mypy src/fileharbor
```

### Run All Quality Checks

```cmd
black src/ tests/ && isort src/ tests/ && flake8 src/ tests/ && mypy src/fileharbor
```

---

## 🗂️ Project Structure in VS Code

```
FILEHARBOR/
├── .vscode/                  # VS Code settings (auto-configured)
│   ├── settings.json         # Editor settings
│   ├── launch.json          # Debug configurations
│   ├── tasks.json           # Tasks (run tests, format, etc.)
│   └── extensions.json      # Recommended extensions
│
├── src/fileharbor/          # Source code
│   ├── common/              # Core utilities
│   ├── utils/               # Helper functions
│   ├── config_tool/         # Configuration CLI
│   ├── server/              # Server implementation
│   └── client/              # Client library
│
├── tests/                   # Test suite
│   ├── test_common/         # Unit tests
│   ├── test_integration/    # Integration tests
│   ├── test_security/       # Security tests
│   ├── test_e2e/           # End-to-end tests
│   └── test_performance/    # Benchmarks
│
├── examples/                # Example scripts
│
├── environment.yml          # Conda environment
├── pyproject.toml          # Package configuration
├── setup_windows.bat       # Windows setup script
├── test.bat                # Windows test runner
└── run_tests.py            # Cross-platform test runner
```

---

## 🔍 VS Code Features

### IntelliSense

- Auto-completion as you type
- Function signatures
- Documentation on hover
- Type hints

### Testing Integration

- View all tests in Test Explorer
- Run individual tests
- Run test suites
- See test results inline
- Debug failed tests

### Git Integration

- View changes in Source Control panel
- Commit changes
- Push/pull
- View file history
- Diff viewer

### Terminal

- Integrated terminal (`` Ctrl+` ``)
- Multiple terminals
- Auto-activates conda environment
- Split terminals

---

## 🚨 Common Issues and Solutions

### Issue: "conda not found"

**Solution:**
1. Restart terminal after installing Miniconda
2. Or add Miniconda to PATH:
   - Search for "Environment Variables" in Windows
   - Add: `C:\Users\YourName\miniconda3\Scripts`
   - Add: `C:\Users\YourName\miniconda3\Library\bin`

### Issue: "fileharbor-server not found"

**Solution:**
```cmd
# Ensure you're in the fileharbor environment
conda activate fileharbor

# Reinstall in development mode
pip install -e .
```

### Issue: Tests failing with import errors

**Solution:**
```cmd
# Make sure package is installed
pip install -e .

# Or set PYTHONPATH
set PYTHONPATH=%CD%\src
```

### Issue: VS Code not finding Python interpreter

**Solution:**
1. Press `Ctrl+Shift+P`
2. "Python: Select Interpreter"
3. Click "Enter interpreter path..."
4. Browse to: `C:\Users\YourName\miniconda3\envs\fileharbor\python.exe`

### Issue: Import errors in VS Code but code runs fine

**Solution:**
1. Reload VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"
2. Or update `PYTHONPATH` in `.vscode/settings.json`

### Issue: Port 8443 already in use

**Solution:**
```cmd
# Find process using port
netstat -ano | findstr :8443

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

---

## 💡 Pro Tips

### 1. Use Multiple Terminals

- Open multiple terminals in VS Code
- One for server
- One for tests
- One for client

### 2. Quick File Navigation

- `Ctrl+P` - Quick open file
- `Ctrl+Shift+F` - Search in files
- `Ctrl+G` - Go to line

### 3. Use Snippets

VS Code will suggest completions:
- Type `def` → Function template
- Type `class` → Class template
- Type `if` → If statement

### 4. Testing Shortcuts

- Right-click in test file → "Run Test" or "Debug Test"
- Click gutter icon to run/debug specific test
- Use Test Explorer for visual test navigation

### 5. Terminal Commands

```cmd
# Quick test
pytest tests/test_common/test_validators.py -v -k "test_valid"

# Watch mode (rerun on changes) - requires pytest-watch
ptw -- -v

# Parallel testing (faster) - requires pytest-xdist
pytest -n auto
```

### 6. Environment Management

```cmd
# Create environment backup
conda env export > environment_backup.yml

# Update environment
conda env update -f environment.yml --prune

# List packages
conda list

# Deactivate
conda deactivate
```

---

## 📚 Additional Resources

### Documentation Files

- `README.md` - Project overview
- `CLIENT_QUICK_START.md` - Client usage guide
- `COMPLETION.md` - Feature list
- `PROJECT_STATUS.md` - Project statistics
- `PHASE[3-7]_SUMMARY.md` - Detailed documentation

### Python Documentation

- Type hints: Press `Ctrl` and hover over function
- Function docs: Hover over function name
- Go to definition: `F12` or `Ctrl+Click`
- Find all references: `Shift+F12`

### Conda Commands

```cmd
conda env list                    # List environments
conda list                        # List packages
conda install <package>          # Install package
conda update <package>           # Update package
conda remove <package>           # Remove package
conda env export > env.yml       # Export environment
```

---

## 🎯 Next Steps

1. **Complete Setup:**
   ```cmd
   setup_windows.bat
   ```

2. **Open in VS Code:**
   ```cmd
   code .
   ```

3. **Run Tests:**
   ```cmd
   test.bat
   ```

4. **Create Configuration:**
   ```cmd
   fileharbor-config server_config.json
   ```

5. **Start Development!**

---

## 📞 Getting Help

- Check documentation files
- Use VS Code IntelliSense (hover over code)
- Read docstrings (hover over functions)
- Debug with breakpoints
- Check test examples

---

**Happy coding! 🚀**

Windows development for FileHarbor is now fully configured and ready to use!
