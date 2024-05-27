import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from langsmith import traceable
from langchain_community.tools.shell.tool import ShellTool
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from operator import itemgetter
import subprocess

from pathlib import Path

ROOT_DIR = Path.cwd()


@tool
def create_directory(directory: str):
    """Creates a new writable directory with the given name if it does not exist."""
    directory_path = Path(directory)
    directory_path.mkdir(parents=True, exist_ok=True)
    print(f"Directory '{directory}' created successfully.")


@tool
def find_file(filename: str, path: str):
    """Recursively searches for a file in the given path and returns its path. Returns None if the file is not found."""
    base_path = Path(path)
    for file_path in base_path.rglob(filename):
        if file_path.name == filename:
            return file_path
    return None


@tool
def create_file(
    filename: str, content: str = "", directory=ROOT_DIR, file_type: str = ""
):
    """Creates a new file with specified file type and content in the specified directory."""
    directory_path = Path(directory)
    directory_path.mkdir(
        parents=True, exist_ok=True
    )  # Create directory if it doesn't exist

    # Append the file type extension if provided
    if file_type:
        filename = f"{filename}.{file_type}"

    file_path = (
        directory_path / filename
    )  # Join the directory and filename to form the full path

    # Write the content to the file
    with file_path.open(mode="w", encoding="utf-8") as file:
        file.write(content)

    return file_path


@tool
def read_file(path):
    """Reads the content of a file."""
    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"The file at {path} does not exist.")

    with file_path.open(mode="r", encoding="utf-8") as file:
        content = file.read()

    return content


@tool
def update_file(filename: str, content: str, directory: str = ROOT_DIR):
    """Overwrites an existing file with new content. You should first read_file and then update_file with it's entire contents."""
    directory_path = Path(directory)

    directory_path.mkdir(parents=True, exist_ok=True)

    file_path = directory_path / filename

    with file_path.open(mode="w", encoding="utf-8") as file:
        file.write(content)

    return file_path


# List of tools to use
tools = [
    ShellTool(ask_human_input=True),
    create_directory,
    find_file,
    create_file,
    update_file,
    read_file,
]

# Configure the language model
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Set up the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert web developer.",
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# Bind the tools to the language model
llm_with_tools = llm.bind_tools(tools)

# Create the agent
agent = (
    {
        "input": itemgetter("input"),
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

# Create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Main loop to prompt the user
while True:
    user_prompt = input("Prompt: ")
    list(agent_executor.stream({"input": user_prompt}))
