import os
from mcp.server import MCPServer

mcp = MCPServer("notes_test")
location = os.path.dirname(os.path.abspath(__file__))

def _create_file(filename: str) -> None:
    """ Creates a file if the file of the given file name is not present in the root folder location"""

    file_path = os.path.join(location,f"{filename}.txt")
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("")


@mcp.tool()
def write_notes(filename: str, input: str) -> str:
    """ Writes the given input into the given file"""

    file_path = os.path.join(location, f"{filename}.txt")
    _create_file(filename)
    with open(file_path, "a") as f:
        f.write(f"{input}" + "\n")

    return "Notes saved successfully"

@mcp.tool()
def read_notes(filename: str) -> str:
    """ Reads the content of the given file"""

    file_path = os.path.join(location, f"{filename}.txt")

    if not search_file(filename):
        return "The file does not exist in this path waa waa"

    with open(file_path, "r") as f:
        lines = f.readlines()

    return "".join(lines)

@mcp.resource("search://{filename}")
def search_file(filename: str) -> bool:
    """ Searches whether a file is present or not """

    file_path = os.path.join(location, f"{filename}.txt")

    if os.path.exists(file_path):
        return True
    return False



     