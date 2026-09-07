from mcp.server import MCPServer

mcp = MCPServer("Demo")

@mcp.tool()
def add(a:int, b:int) -> int:
    """Add two numbers"""
    return a+b

@mcp.resource("greet://{s}")
def greet(s:str) -> str:
    """Greets the input value"""
    return f"Hello {s}, Welcome!"

