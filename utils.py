import asyncio
import json
import os
import sys
from enum import Enum

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

MEMORY_FILE = "memory.json"
MEMORY_MAX = 10

USER_PLATFORM = sys.platform
USER_ENV = os.environ.get("TERM", "N/A")


class Agent:
    def __init__(self, use_memory=False) -> None:
        self.client = AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        self.use_memory = use_memory
        self.chat = []
        if self.use_memory:
            self.memory = self.load_memory()

    async def a_run(self, query: str) -> None:
        self.chat.append({"role": "user", "content": query})
        messages = self.chat.copy()

        if self.use_memory:
            messages = self.memory + messages
            memory_message = "You are capable of remembering previous interactions. Your conversation history is stored to a file and loaded into your memory. Use this to improve your responses."
        else:
            memory_message = "You are capable of remembering previous interactions, but only within this session. Your conversation history is not currently stored to between sessions."

        async with self.client.messages.stream(
            system=f"Your primary function is to assist the user with tasks related to terminal commands in their respective platform. You can also help with code and other queries. Ths user's platform is {USER_PLATFORM} and their terminal is {USER_ENV}. Use formatting appropriate for the user's terminal. {memory_message}",
            max_tokens=1024,
            messages=messages,
            model="claude-3-sonnet-20240229",
        ) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)
            print()

        message = await stream.get_final_message()

        try:
            response = message.content[0].text
            self.chat.append({"role": "assistant", "content": response})
            if self.use_memory:
                self.save_memory(query, response)
        except Exception as e:
            print(f"Error (claude): {e}")

    def run(self, query: str) -> None:
        asyncio.run(self.a_run(query))

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


USER_STYLE_PREFIX = f"{PrintStyle.BLUE.value}"
