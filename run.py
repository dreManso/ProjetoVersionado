import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

URL = "http://localhost:8000"


def main():
    if "--sem-atualizar" not in sys.argv:
        from app import updater
        if updater.check_and_update():
            # Reabre já com os arquivos novos
            sys.exit(subprocess.call([sys.executable, str(Path(__file__).resolve()), "--sem-atualizar"]))

    import uvicorn
    from app.version import __version__

    print(f"Controle de Cozinha v{__version__} rodando em {URL}")
    print("Deixe esta janela aberta enquanto usa o programa. Para desligar, feche-a ou aperte Ctrl+C.")
    threading.Timer(2.0, lambda: webbrowser.open(URL)).start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
