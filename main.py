import json
import cmd2
from server.server import VoIPServer
from threading import Thread


class VoIPServerCLI(cmd2.Cmd):
    def __init__(self, port=8080, host="localhost"):
        super().__init__()
        self.intro = "Welcome to the VoIP Server CLI. Type help or ? to list commands."
        self.prompt = "(VoIPServerCLI) "
        self.port = port
        self.host = host
        self.server = VoIPServer(self.port, self.host)

    def do_start(self, arg):
        """Start the VoIP server. Usage: start"""
        if self.server and self.server.is_alive():
            self.poutput("Server is already running.")
        else:
            self.poutput("Starting VoIP server...")
            self.server.start()

    def do_stop(self, arg):
        """Stop the VoIP server. Usage: stop"""
        if self.server and self.server.is_alive():
            self.poutput("Stopping VoIP server...")
            self.server.stop()
            self.poutput("Server stopped.")
            self.server = VoIPServer(self.port, self.host)
        else:
            self.poutput("Server is not running.")

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

    def do_clear(self, arg):
        """Clear the console. Usage: clear"""
        self.poutput("\033c")

    def do_exit(self, arg):
        """Exit the CLI."""
        self.do_stop(arg)
        return True

if __name__ == '__main__':
    with open('server/settings.json', 'r') as f:
        settings = json.load(f)

    app = VoIPServerCLI(port=settings["server"]["port"], host=settings["server"]["host"])
    app.cmdloop()
