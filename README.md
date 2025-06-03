# darkboss1-Find-The-Admin-Panel-Advanced
- **Advanced Scanning**: Multiple scan modes (aggressive, stealth, simple)
- **Smart Detection**: Analyzes responses to identify potential admin panels
- **Enhanced Logging**: Comprehensive logging system with separate logs for errors, warnings, and usage
- **Configuration System**: All settings are centralized in `config.json`
- **Ctrl+C Handling**: Press once to stop scan and show results, press twice to exit
- **Export Options**: Export results to multiple formats (JSON, HTML, CSV, TXT)
- **Performance**: Asynchronous processing and concurrent requests for faster scanning
- **User-Friendly**: Rich terminal interface with progress tracking and statistics

## Installation

```bash
# Clone the repository
git clone https://github.com/darkboss1/darkboss1-Find-The-Admin-Panel-Advanced.git
cd darkboss1-Find-The-Admin-Panel-Advanced

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python finder.py -u https://example.com
```

### Advanced Options

```bash
python finder.py -u https://example.com --mode aggressive --concurrency 50 -j -h -c
```

### Parameters

- `-u, --url`: Target URL to scan
- `--mode`: Scan mode (aggressive, stealth, simple, all)
- `-p, --paths`: Path to the paths file (default: general_paths.json)
- `-c, --concurrency`: Number of concurrent requests (default: from config.json)
- `-t, --timeout`: Request timeout in seconds (default: from config.json)
- `-j, --json`: Export results to JSON
- `-h, --html`: Export results to HTML
- `--csv`: Export results to CSV
- `--txt`: Export results to TXT
- `--no-verify`: Disable SSL verification
- `--output`: Output file prefix

## Configuration

All settings are stored in `config/config.json`. This centralized approach allows for easy customization without modifying the source code.

#Develope By
#Telegram: https://t.me/darkboss1bd
