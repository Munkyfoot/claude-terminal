# Claude Terminal

Claude Terminal is a Python-based command-line interface (CLI) tool that allows you to interact with Anthropic's Claude, an AI assistant. It provides a convenient way to chat with Claude and get assistance with various tasks, including terminal commands, code, and other queries. Claude Terminal now supports function calling, which enables the writing of files based on user interactions.

## Features

- Chat with Claude directly from your terminal
- Get assistance with terminal commands specific to your platform (Linux, Windows, or macOS)
- Receive help with code and other queries
- Optionally store conversation history to improve responses over time
- **New**: Function calling support, enabling file writing based on user interactions

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Anthropic API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Munkyfoot/claude-terminal.git
```

2. Navigate to the project directory:

```bash
cd claude-terminal
```

3. Create a virtual environment:

```bash
python -m venv venv
```

4. Activate the virtual environment:

- For Linux/macOS:

```bash
source venv/bin/activate
```

- For Windows:

```batch
venv\Scripts\activate
```

5. Install the required dependencies:

```bash
pip install -r requirements.txt
```

6. Rename `.env.example` to `.env`:

```bash
mv .env.example .env
```

- Then open the `.env` file in a text editor and add your Anthropic API key:

```
ANTHROPIC_API_KEY="YOUR_API_KEY"
```

## Usage

To run Claude Terminal, use the following command:

```bash
python main.py [query] [flags]
```

- `query`: Optional initial query to start the conversation
- `flags`:
  - `--memory` or `-m`: Save/load conversation history to add long-term memory to the conversation

Example (without initial query):

```bash
python main.py
```

**Note:** If you don't provide an initial query, you can start the conversation by typing your first message after running the command.

Example (with initial query):

```bash
python main.py "How can I list files in a directory?"
```

**Note:** If you provide an initial query, the conversation will start with that query. You don't need to use quotes for the query, but it is recommended to do so to avoid issues with special characters.

Example (with initial query and memory):

```bash
python main.py "How can I list files in a directory?" --memory
```

**Note:** If you provide the `--memory` flag, previous conversation history will be loaded and any new conversation history will be saved to long-term memory in the `memory.json` file. The number of messages saved to memory is limited to value specified in MEMORY_MAX in the `utils.py` file.

## File Writing with Function Calls

Claude Terminal now supports function calling, which allows Claude to write files based on user interactions. When Claude generates a response that includes a function call, you will be prompted to confirm whether you want to execute the function.

If you choose to run the function, Claude Terminal will process the function call and write the specified file(s) to the designated path(s) relative to the current working directory. The tool will create any necessary directories if they don't already exist.

After the file writing is complete, Claude will provide a final response based on the executed function and the conversation context.

## Running from Anywhere

To run Claude Terminal from anywhere in your terminal, you can set up a script and add it to your system's PATH.

### Linux

1. Create a new file named `ask` (without any file extension) in the project directory.

2. Open the `ask` file in a text editor and add the following content:

```bash
#!/bin/bash

# Activate the virtual environment
source /path/to/claude-terminal/venv/bin/activate

# Run the Python script with the provided arguments
python /path/to/claude-terminal/main.py "$@"

# Deactivate the virtual environment
deactivate
```

3. Make the `ask` file executable:

```bash
chmod +x /path/to/claude-terminal/ask
```

4. Create a symbolic link to the `ask` file in a directory that is in your system's PATH (e.g., `~/bin`):

```bash
mkdir -p ~/bin
ln -s /path/to/claude-terminal/ask ~/bin/ask
```

5. Add `~/bin` to your system's PATH in your `~/.bashrc` file:

```bash
export PATH="$HOME/bin:$PATH"
```

6. Reload the configuration:

```bash
source ~/.bashrc
```

Now you can run Claude Terminal from anywhere using the `ask` command:

```bash
ask "How can I list files in a directory?"
```

### macOS

1. Create a new file named `ask` (without any file extension) in the project directory.

2. Open the `ask` file in a text editor and add the following content:

```bash
#!/bin/bash

# Activate the virtual environment
source /path/to/claude-terminal/venv/bin/activate

# Run the Python script with the provided arguments
python /path/to/claude-terminal/main.py "$@"

# Deactivate the virtual environment
deactivate
```

3. Make the `ask` file executable:

```bash
chmod +x /path/to/claude-terminal/ask
```

4. Create a symbolic link to the `ask` file in a directory that is in your system's PATH (e.g., `/usr/local/bin`):

```bash
sudo ln -s /path/to/claude-terminal/ask /usr/local/bin/ask
```

Now you can run Claude Terminal from anywhere using the `ask` command:

```bash
ask "How can I list files in a directory?"
```

### Windows

1. Create a new file named `ask.bat` in the project directory.

2. Open the `ask.bat` file in a text editor and add the following content:

```batch
@echo off

REM Activate the virtual environment
call C:\path\to\claude-terminal\venv\Scripts\activate.bat

REM Run the Python script with the provided arguments
python C:\path\to\claude-terminal\main.py %*

REM Deactivate the virtual environment
call C:\path\to\claude-terminal\venv\Scripts\deactivate.bat
```

3. Add the project directory to your system's PATH environment variable:

   - Open the Start menu and search for "Environment Variables"
   - Click on "Edit the system environment variables"
   - In the System Properties window, click on the "Environment Variables" button
   - Under "System variables", scroll down and find the "Path" variable, then click on "Edit"
   - Click on "New" and add the path to your project directory (e.g., `C:\path\to\claude-terminal`)
   - Click "OK" to close all the windows

4. Open a new command prompt window to ensure the updated PATH is loaded.

Now you can run Claude Terminal from anywhere using the `ask` command:

```batch
ask "How can I list files in a directory?"
```
