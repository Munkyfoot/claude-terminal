import json
import os
import re
import sys
from enum import Enum
from typing import Literal

from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
MEMORY_FILE = "memory.json"
MEMORY_MAX = 24  # Used to limit the number of messages stored in memory (applies to short and long-term memory)

# User's platform and environment information
USER_PLATFORM = sys.platform

if USER_PLATFORM == "win32":
    USER_ENV = os.environ.get("COMSPEC")
else:
    USER_ENV = os.environ.get("SHELL", "unknown")

USER_CWD = os.getcwd()

USER_INFO = f"""User's Information:
- Platform: {USER_PLATFORM}
- Environment: {USER_ENV}
- Current Working Directory: {USER_CWD}
"""


def get_files_dirs(use_gitignore=True, ignore_all_hidden=False):
    output = []

    # Read .gitignore file if use_gitignore is True
    gitignore_entries = set()
    if use_gitignore:
        gitignore_path = os.path.join(USER_CWD, ".gitignore")
        if os.path.isfile(gitignore_path):
            with open(gitignore_path, "r") as file:
                gitignore_entries = {line.strip() for line in file}

    # Helper function to check if an item should be excluded based on .gitignore
    def is_excluded(item_path):
        rel_path = os.path.relpath(item_path, USER_CWD)
        rel_path = os.path.normpath(rel_path).replace(os.sep, "/")
        if rel_path in gitignore_entries or f"{rel_path}/" in gitignore_entries:
            return True
        return any(
            entry.endswith("/") and rel_path.startswith(entry)
            for entry in gitignore_entries
        )

    # Helper function to build the file tree
    def tree(dir_path, indent=""):
        try:
            dir_content = [
                item
                for item in os.listdir(dir_path)
                if not item.startswith(".git")
                and (not ignore_all_hidden or not item.startswith("."))
            ]
            dir_content.sort()
            for item in dir_content:
                item_path = os.path.join(dir_path, item)
                if not is_excluded(item_path):
                    rel_path = os.path.relpath(item_path, USER_CWD)
                    rel_path = os.path.normpath(rel_path).replace(os.sep, "/")
                    if os.path.isdir(item_path):
                        output.append(f"{indent}{rel_path}/")
                        tree(item_path, indent + "  ")
                    else:
                        output.append(f"{indent}{rel_path}")
        except PermissionError:
            output.append(f"{indent}Permission denied: {dir_path}")

    # Start building the tree from the current working directory
    tree(USER_CWD)

    return "\n".join(output)


def write_file(file_path, content):
    print(
        f"{PrintStyle.GREEN.value}Writing to file '{file_path}'...{PrintStyle.RESET.value}"
    )
    file_path = os.path.join(USER_CWD, file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as file:
        file.write(content)
    return f"File '{file_path}' written successfully."


def write_files(files_dict):
    results = []
    for file_path, content in files_dict.items():
        result = write_file(file_path, content)
        results.append(result)
    return "\n".join(results)


def read_file(file_path):
    print(
        f"{PrintStyle.GREEN.value}Reading file '{file_path}'...{PrintStyle.RESET.value}"
    )
    file_path = os.path.join(USER_CWD, file_path)
    try:
        with open(file_path, "r") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return f"File '{file_path}' not found."


def read_files(file_paths):
    results = []
    for file_path in file_paths:
        result = f"`{file_path}`:\n```{read_file(file_path)}```"
        results.append(result)
    return "\n\n".join(results)


def construct_format_tool_for_claude_prompt(name, description, parameters):
    constructed_prompt = (
        "<tool_description>\n"
        f"<tool_name>{name}</tool_name>\n"
        "<description>\n"
        f"{description}\n"
        "</description>\n"
        "<parameters>\n"
        f"{construct_format_parameters_prompt(parameters)}\n"
        "</parameters>\n"
        "</tool_description>"
    )
    return constructed_prompt


def construct_format_parameters_prompt(parameters):
    constructed_prompt = "\n".join(
        f"<parameter>\n<name>{parameter['name']}</name>\n<type>{parameter['type']}</type>\n<description>{parameter['description']}</description>\n</parameter>"
        for parameter in parameters
    )
    return constructed_prompt


FILE_WRITER_TOOL = construct_format_tool_for_claude_prompt(
    name="file_writer",
    description="Writes content to a file at the specified path relative to the current working directory, creating directories if necessary.",
    parameters=[
        {
            "name": "file_path",
            "type": "str",
            "description": "The path of the file to create (relative to the current working directory).",
        },
        {
            "name": "content",
            "type": "str",
            "description": "The content to write to the file.",
        },
    ],
)

FILE_WRITER_MULTIPLE_TOOL = construct_format_tool_for_claude_prompt(
    name="file_writer_multiple",
    description="Writes content to multiple files at the specified paths relative to the current working directory, creating directories if necessary.",
    parameters=[
        {
            "name": "files_dict",
            "type": "dict",
            "description": "A dictionary where the keys are file paths (relative to the current working directory) and the values are the content to write to each file. Be sure to use json format for the dictionary/object. Keys and values should be single-line strings. Use the escape character for newlines.",
        },
    ],
)

FILE_READER_TOOL = construct_format_tool_for_claude_prompt(
    name="file_reader",
    description="Reads the content of a file at the specified path relative to the current working directory.",
    parameters=[
        {
            "name": "file_path",
            "type": "str",
            "description": "The path of the file to read (relative to the current working directory).",
        }
    ],
)

FILE_READER_MULTIPLE_TOOL = construct_format_tool_for_claude_prompt(
    name="file_reader_multiple",
    description="Reads the content of multiple files at the specified paths relative to the current working directory.",
    parameters=[
        {
            "name": "file_paths",
            "type": "list",
            "description": "A list of file paths (relative to the current working directory) to read.",
        }
    ],
)


def construct_tool_use_system_prompt(tools):
    tool_use_system_prompt = (
        "In this environment you have access to a set of tools you can use to answer the user's question. You should only use these tools if specifically requested to perform an action that requires them.\n"
        "\n"
        "You may call them like this:\n"
        "<function_calls>\n"
        "<invoke>\n"
        "<tool_name>$TOOL_NAME</tool_name>\n"
        "<parameters>\n"
        "<$PARAMETER_NAME>$PARAMETER_VALUE</$PARAMETER_NAME>\n"
        "...\n"
        "</parameters>\n"
        "</invoke>\n"
        "</function_calls>\n"
        "\n"
        "Here are the tools available:\n"
        "<tools>\n" + "\n".join([tool for tool in tools]) + "\n</tools>"
    )
    return tool_use_system_prompt


def extract_between_tags(tag: str, string: str, strip: bool = False) -> list[str]:
    ext_list = re.findall(f"<{tag}>(.*?)</{tag}>", string, re.DOTALL)
    if strip:
        ext_list = [e.strip() for e in ext_list]
    return ext_list


def construct_successful_function_run_injection_prompt(invoke_results):
    constructed_prompt = (
        "<function_results>\n"
        + "\n".join(
            f"<result>\n<tool_name>{res['tool_name']}</tool_name>\n<stdout>\n{res['tool_result']}\n</stdout>\n</result>"
            for res in invoke_results
        )
        + "\n</function_results>"
    )
    return constructed_prompt


class Agent:
    def __init__(
        self,
        model: Literal[
            "claude-3-opus-20240229", "claude-3-sonnet-20240229"
        ] = "claude-3-sonnet-20240229",
        use_memory=False,
        view_list_dir=False,
    ) -> None:
        self.client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.model = model
        self.use_memory = use_memory
        self.chat = []
        if self.use_memory:
            self.load_memory()
        self.view_list_dir = view_list_dir
        self.system_prompt = f"Your primary function is to assist the user with tasks related to terminal commands in their respective platform. You can also help with code and other queries. Information about the user's platform, environment, and current working directory is provided below.\n\n{USER_INFO}"

    def run(self, query: str) -> None:
        self.chat.append({"role": "user", "content": query})

        full_system_prompt = f"""{self.system_prompt}\n\n{construct_tool_use_system_prompt(
                [
                    FILE_WRITER_TOOL,
                    FILE_WRITER_MULTIPLE_TOOL,
                    FILE_READER_TOOL,
                    FILE_READER_MULTIPLE_TOOL,
                ]
            )}"""

        if self.view_list_dir:
            files_tree = get_files_dirs()
            full_system_prompt += f"\n\nHere's a list of files and directories in the current working directory:\n\n{files_tree}"

        if self.use_memory:
            _messages = self.memory + self.chat
        else:
            _messages = self.chat

        _messages = _messages[-MEMORY_MAX:]

        with self.client.messages.stream(
            system=full_system_prompt,
            max_tokens=4096,
            messages=_messages,
            model=self.model,
            stop_sequences=["</function_calls>"],
        ) as stream:
            text_stream_content = ""
            function_call_detected = False
            for text in stream.text_stream:
                text_stream_content += text

                if (
                    "<function_calls>" in text_stream_content
                    and not function_call_detected
                ):
                    # Clear and overwrite the current line
                    print("\033[K", end="\r")
                    print(f"{PrintStyle.GREEN.value}<function_calls>", flush=True)
                    function_call_detected = True

                print(text, end="", flush=True)
            print(PrintStyle.RESET.value)

        message = stream.get_final_message().content[0].text

        run_functions = False
        if "<function_calls>" in message:
            if input("Run function calls? (y/[n]): ").lower() == "y":
                print(
                    f"{PrintStyle.GREEN.value}Running functions...{PrintStyle.RESET.value}"
                )
                run_functions = True
            else:
                print(
                    f"{PrintStyle.YELLOW.value}Aborted running functions.{PrintStyle.RESET.value}"
                )
                message = "Aborted running functions."

        if run_functions:
            try:
                message = message + "</function_calls>"
                function_calls = extract_between_tags("function_calls", message)

                def process_function_call(tool_name, function_call, query, message):
                    if tool_name == "file_writer":
                        file_name = extract_between_tags("file_path", function_call)[0]
                        content = extract_between_tags("content", function_call)[0]
                        result = write_file(file_name, content)
                    elif tool_name == "file_writer_multiple":
                        files_dict_str = extract_between_tags(
                            "files_dict", function_call
                        )[0]
                        files_dict = json.loads(files_dict_str)
                        result = write_files(files_dict)
                    elif tool_name == "file_reader":
                        file_name = extract_between_tags("file_path", function_call)[0]
                        result = read_file(file_name)
                    elif tool_name == "file_reader_multiple":
                        file_paths = json.loads(
                            extract_between_tags("file_paths", function_call)[0]
                        )
                        result = read_files(file_paths)
                    else:
                        return False

                    function_results = (
                        construct_successful_function_run_injection_prompt(
                            [{"tool_name": tool_name, "tool_result": result}]
                        )
                    )
                    partial_assistant_message = f"{message}\n\n{function_results}\n\nHere's a brief summary of what was done and what to do next:"

                    final_message = (
                        self.client.messages.create(
                            model=self.model,
                            max_tokens=512,
                            messages=[
                                {"role": "user", "content": query},
                                {
                                    "role": "assistant",
                                    "content": partial_assistant_message,
                                },
                            ],
                            system=f"{self.system_prompt}\n\nYou cannot make any more function calls in this response.",
                        )
                        .content[0]
                        .text
                    )

                    print(final_message)

                    self.chat.append(
                        {
                            "role": "assistant",
                            "content": f"{partial_assistant_message}\n\n{final_message}",
                        }
                    )

                    return True

                for function_call in function_calls:
                    tool_name = extract_between_tags("tool_name", function_call)[0]
                    result = process_function_call(
                        tool_name, function_call, query, message
                    )

                    if result is False:
                        self.chat.append({"role": "assistant", "content": message})
                        break
            except Exception as e:
                print(
                    f"{PrintStyle.RED.value}An error occurred while running the function calls: {e}{PrintStyle.RESET.value}"
                )
                self.chat.append(
                    {
                        "role": "assistant",
                        "content": f"{message}\n\nAn error occurred while running the function calls: {e}",
                    }
                )
        else:
            self.chat.append({"role": "assistant", "content": message})

        if self.use_memory:
            self.save_memory()

    def save_memory(self) -> None:
        memory = (self.memory + self.chat)[-MEMORY_MAX:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f)

    def load_memory(self) -> None:
        self.chat = []
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                self.memory = json.load(f)
        else:
            self.memory = []


class PrintStyle(Enum):
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    INVERT = "\033[7m"
    STRIKETHROUGH = "\033[9m"
    BOLD_END = "\033[21m"
    UNDERLINE_END = "\033[24m"
    INVERT_END = "\033[27m"
    STRIKETHROUGH_END = "\033[29m"
    RESET = "\033[0m"


# User's input style prefix
USER_STYLE_PREFIX = f"{PrintStyle.BLUE.value}"
