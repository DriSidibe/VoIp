from api import VoIPClient
import cmd2

class VoIPClientCLI(cmd2.Cmd):
    def __init__(self, id, host='127.0.0.1', port=8080):
        super().__init__()
        self.intro = "Welcome to the VoIP Client CLI. Type help or ? to list commands."
        self.host = host
        self.port = port
        self.id = id
        self.prompt = "(VoIPClientCLI) "
        self.client = VoIPClient(id=self.id, host=self.host, port=self.port)

    def do_connect(self, arg):
        """Connect the client to the server. Usage: connect"""
        self.client.connect_to_server()

    def do_disconnect(self, arg):
        """Disconnect the client from the server. Usage: disconnect"""
        self.client.disconnect()
        self.client = VoIPClient(self.id, self.host, self.port)

    def do_status(self, arg):
        """Check client status on the server. Usage: status"""
        self.client.status()

    def do_clear(self, arg):
        """Clear the console. Usage: clear"""
        self.poutput("\033c")

    def do_exit(self, arg):
        """Exit the CLI."""
        self.poutput("Exiting the VoIP Client CLI.")
        self.do_disconnect(arg)
        return True

if __name__ == '__main__':
    app = VoIPClientCLI(id="185bd454-6d73-4990-b75b-d4aa87a95e4f", host="127.0.0.1", port=8080)
    app.cmdloop()