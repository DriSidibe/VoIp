import cmd2
import sys

from client.api import VoIPClient

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
        try:
            self.client.client_socket.close()
        except:
            pass
        self.client = VoIPClient(self.id, self.host, self.port)
        
    def do_send_text(self, arg):
        """Send a text message to someone. Usage: send_text <recipient_username> <message>"""
        self.client.text_friend(arg)
    
    def do_get_messages(self, arg):
        """Get messages from someone. Usage: get_messages <from_date | None> <to_date | None> <from_user | None>"""
        self.client.get_messages(arg)

    def do_status(self, arg):
        """Check client status on the server. Usage: status"""
        self.client.status()

    def do_friends_list(self, arg):
        """Check all available friends on the server. Usage: friends_list"""
        self.client.friends_list()

    def do_clear(self, arg):
        """Clear the console. Usage: clear"""
        self.poutput("\033c")

    def do_exit(self, arg):
        """Exit the CLI."""
        self.poutput("Exiting the VoIP Client CLI.")
        self.do_disconnect(arg)
        return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python main.py <client_id>")
        sys.exit(1)
    app = VoIPClientCLI(id=sys.argv[1], host="127.0.0.1", port=8080)
    app.cmdloop()