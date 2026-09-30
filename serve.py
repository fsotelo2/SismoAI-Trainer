"""
Servidor HTTP simple para desarrollo de SismoAI Trainer Web.
Permite ver la aplicación en un navegador normal mientras pywebview no está disponible.
"""

import http.server
import socketserver
import os
import sys
import webbrowser
from threading import Timer

PORT = 8080
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format, *args):
        # Suppress log messages
        pass


def open_browser():
    """Open the browser after a short delay."""
    webbrowser.open(f'http://localhost:{PORT}')


def main():
    """Start the development server."""

    # Change to the UI directory
    os.chdir(DIRECTORY)

    # Create the server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Servidor iniciado en http://localhost:{PORT}")
        print("Presiona Ctrl+C para detener")

        # Open browser after 1 second
        Timer(1.0, open_browser).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")
            sys.exit(0)


if __name__ == '__main__':
    main()
