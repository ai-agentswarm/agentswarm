from agentswarm.datamodels import Message

class Colors:
    """ANSI Colors for console output"""
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GRAY = '\033[90m'

def print_message(message: Message):
    """Print a message formatted based on its type"""
    content = message.content.strip()
    
    if message.type == "user":
        print(f"\n{Colors.BOLD}{Colors.BLUE}👤 Tu:{Colors.END}")
        print(f"{Colors.BLUE}{content}{Colors.END}")
    elif message.type == "assistant":
        print(f"\n{Colors.BOLD}{Colors.GREEN}🤖 Assistant:{Colors.END}")
        print(f"{Colors.GREEN}{content}{Colors.END}")
    elif message.type == "system":
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⚙️  System:{Colors.END}")
        print(f"{Colors.YELLOW}{content}{Colors.END}")
    else:
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}📎 {message.type}:{Colors.END}")
        print(f"{Colors.MAGENTA}{content}{Colors.END}")


def print_separator():
    """Print a separator"""
    print(f"{Colors.GRAY}{'─' * 80}{Colors.END}")


def get_user_input() -> str:
    """Get user input with a nice prompt"""
    print(f"\n{Colors.GRAY}{'─' * 80}{Colors.END}")
    return input(f"{Colors.BOLD}{Colors.CYAN}💬 You: {Colors.END} {Colors.GRAY}(type 'exit' to exit){Colors.END}\n{Colors.CYAN}→{Colors.END} ")
