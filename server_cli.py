import cmd2
from server import server
from utils.utils import get_all_settings_from_json

class VoIPServerCLI(cmd2.Cmd):
    def __init__(self, host: str, port: int):
        super().__init__()
        self.intro = "Welcome to the VoIP Server CLI. Type help or ? to list commands."
        self.prompt = "(VoIPServerCLI) "
        self.port = port
        self.host = host
        self.server = server.VoIPServer(host, port)

    def do_describe(self, arg):
        """Get infos on the VoIP server. Usage: describe"""
        self.server.describe()

    def do_start(self, arg):
        """Start the VoIP server. Usage: start"""
        if self.server.running:
            self.poutput("Server is already running.")
        else:
            self.poutput("Starting VoIP server...")
            self.server.start()
            self.poutput(f"Starting server on {self.host}:{self.port}...")

    def do_stop(self, arg):
        """Stop the VoIP server. Usage: stop"""
        if not self.server.running:
            self.poutput("Server is not running.")
            return
        self.server.stop()

    def do_status(self, arg):
        """Check if the VoIP server is running."""
        if self.server and self.server.is_alive():
            self.poutput("Server is running.")
        else:
            self.poutput("Server is stopped.")

    def do_all_clients(self, arg):
        """List all clients. Usage: all_clients"""
        if self.server.clients:
            self.poutput("All clients:")
            for client in self.server.clients:
                self.poutput(f"ID: {client['id']}, Username: {client['username']}")
        else:
            self.poutput("No clients connected.")

    def do_clients(self, arg):
        """List connected clients. Usage: clients"""
        if self.server.available_clients:
            self.poutput("Connected clients:")
            for client in self.server.available_clients:
                self.poutput(f"ID: {client['id']}, Socket: {client['socket']}")
        else:
            self.poutput("No clients connected.")

    def do_status(self, arg):
        """Check server status. Usage: status"""
        if self.server.running:
            self.poutput("Server is running.")
        else:
            self.poutput("Server is stopped.")

    def do_clear(self, arg):
        """Clear the console. Usage: clear"""
        self.poutput("\033c")

    def do_exit(self, arg):
        """Exit the CLI."""
        self.do_stop(arg)
        return True

if __name__ == '__main__':
    settings = get_all_settings_from_json()
    try:
        port = settings['server']['port']
        host = settings['server']['host']
    except KeyError:
        port, host = None, None

    if not (port and host):
        host, port = "localhost", 8080

    app = VoIPServerCLI(host, port)
    app.cmdloop()
