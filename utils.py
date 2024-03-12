import json
import os
import re
import sys
from enum import Enum

from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
MEMORY_FILE = "memory.json"
MEMORY_MAX = 10

# User's platform and environment information
USER_PLATFORM = sys.platform

if USER_PLATFORM == "win32":
    USER_ENV = os.environ.get("COMSPEC")
else:
    USER_ENV = os.environ.get("SHELL", "unknown")

USER_CWD = os.getcwd()
USER_CWD_FILES = os.listdir(USER_CWD)

USER_INFO = f"""User's Information:
- Platform: {USER_PLATFORM}
- Environment: {USER_ENV}
- Current Working Directory: {USER_CWD}
- Files in Current Working Directory: {USER_CWD_FILES}
"""


def write_file(file_path, content):
    print(f"Writing to file '{file_path}'...")
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
            "description": "A dictionary where the keys are file paths (relative to the current working directory) and the values are the content to write to each file. Be sure to wrap the keys and values in quotes.",
        },
    ],
)


def construct_tool_use_system_prompt(tools):
    tool_use_system_prompt = (
        "In this environment you have access to a set of tools you can use to answer the user's question.\n"
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
    def __init__(self, use_memory=False) -> None:
        self.client = Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.model = "claude-3-sonnet-20240229"
        self.use_memory = use_memory
        self.chat = []
        if self.use_memory:
            self.memory = self.load_memory()
        self.system_prompt = (
            f"Your primary function is to assist the user with tasks related to terminal commands in their respective platform. You can also help with code and other queries. Information about the user's platform, environment, and current working directory is provided below.\n\n{USER_INFO}\n\n"
            + construct_tool_use_system_prompt(
                [FILE_WRITER_TOOL, FILE_WRITER_MULTIPLE_TOOL]
            )
        )

    def run(self, query: str) -> None:
        self.chat.append({"role": "user", "content": query})
        messages = [{"role": "user", "content": query}]

        with self.client.messages.stream(
            system=self.system_prompt,
            max_tokens=1024,
            messages=messages,
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
                    print(" " * len("<function_calls>"), end="\r", flush=True)
                    function_call_detected = True

                if not function_call_detected:
                    print(text, end="", flush=True)
            print()

        message = stream.get_final_message().content[0].text

        if "<function_calls>" in message:
            message = message + "</function_calls>"
            function_calls = extract_between_tags("function_calls", message)
            for function_call in function_calls:
                tool_name = extract_between_tags("tool_name", function_call)[0]
                if tool_name == "file_writer":
                    file_name = extract_between_tags("file_path", function_call)[0]
                    content = extract_between_tags("content", function_call)[0]
                    result = write_file(file_name, content)
                    function_results = (
                        construct_successful_function_run_injection_prompt(
                            [{"tool_name": "file_writer", "tool_result": result}]
                        )
                    )
                    partial_assistant_message = message + function_results

                    final_message = (
                        self.client.messages.create(
                            model=self.model,
                            max_tokens=1024,
                            messages=[
                                {"role": "user", "content": query},
                                {
                                    "role": "assistant",
                                    "content": partial_assistant_message,
                                },
                            ],
                            system=self.system_prompt,
                        )
                        .content[0]
                        .text
                    )

                    print(final_message)

                    messages.append({"role": "assistant", "content": final_message})
                    break
                elif tool_name == "file_writer_multiple":
                    files_dict_str = extract_between_tags("files_dict", function_call)[
                        0
                    ]
                    files_dict = json.loads(files_dict_str)
                    result = write_files(files_dict)
                    function_results = (
                        construct_successful_function_run_injection_prompt(
                            [
                                {
                                    "tool_name": "file_writer_multiple",
                                    "tool_result": result,
                                }
                            ]
                        )
                    )
                    partial_assistant_message = message + function_results

                    final_message = (
                        self.client.messages.create(
                            model=self.model,
                            max_tokens=1024,
                            messages=[
                                {"role": "user", "content": query},
                                {
                                    "role": "assistant",
                                    "content": partial_assistant_message,
                                },
                            ],
                            system=self.system_prompt,
                        )
                        .content[0]
                        .text
                    )

                    print(final_message)

                    messages.append({"role": "assistant", "content": final_message})
                    break
                else:
                    messages.append({"role": "assistant", "content": message})
                    break
        else:
            messages.append({"role": "assistant", "content": message})

        if self.use_memory:
            self.save_memory(query, messages[-1]["content"])

    def save_memory(self, query: str, response: str) -> None:
        memory = self.load_memory()
        memory = memory + [
            {"role": "user", "content": query},
            {"role": "assistant", "content": response},
        ]
        if len(memory) > MEMORY_MAX:
            memory = memory[-MEMORY_MAX:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f)

    def load_memory(self) -> list[tuple[str, str]]:
        if not os.path.exists(MEMORY_FILE):
            return []
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)


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
