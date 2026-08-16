import secrets

class AgentState:
    def __init__(self):
        # Generate a random 4-digit pairing PIN
        self.pairing_pin = f"{secrets.randbelow(10000):04d}"
        # Set of active authorized session tokens
        self.active_tokens = set()
        # Active port the server is running on
        self.port = 8000
        # Hostname of the current machine
        self.hostname = ""
        # Local IP address
        self.local_ip = ""

    def generate_token(self) -> str:
        token = secrets.token_hex(32)
        self.active_tokens.add(token)
        return token

    def verify_token(self, token: str) -> bool:
        return token in self.active_tokens

# Global state instance
state = AgentState()
