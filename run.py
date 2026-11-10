import threading
import webbrowser

import uvicorn

from app.version import __version__

URL = "http://localhost:8000"

if __name__ == "__main__":
    print(f"Controle de Cozinha v{__version__} rodando em {URL}")
    print("Deixe esta janela aberta enquanto usa o programa. Para desligar, feche-a ou aperte Ctrl+C.")
    threading.Timer(2.0, lambda: webbrowser.open(URL)).start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
