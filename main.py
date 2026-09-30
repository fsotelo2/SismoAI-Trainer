"""
SismoAI Trainer — Web Entry Point
Inicializa pywebview con Edge Chromium / WebView2 y lanza la aplicación.
"""

import os
import sys

# Add project root and core to path for imports
_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'core'))

import webview
from bridge.api_bridge import ApiBridge


def main():
    """Initialize and run the SismoAI Trainer web application."""

    # Get the path to the UI directory
    ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')
    index_path = os.path.join(ui_dir, 'index.html')

    # Verify UI exists
    if not os.path.exists(index_path):
        print(f"Error: No se encontró {index_path}")
        sys.exit(1)

    # Create the API bridge
    api = ApiBridge()

    # Create the webview window
    window = webview.create_window(
        title='SismoAI Trainer',
        url=index_path,
        js_api=api,
        width=1400,
        height=900,
        min_size=(1024, 700),
        text_select=True,
    )

    # Start the application
    webview.start(
        debug=False,  # Set to True for DevTools access
        gui='edgechromium',  # Use Edge Chromium on Windows
    )


if __name__ == '__main__':
    main()
