import json
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path

URL = "http://localhost:8000"


def running_version():
    """Versão do programa já aberto na porta 8000; None se a porta está livre; '?' se não der para saber."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # localhost: sem proxy
    try:
        with opener.open("http://127.0.0.1:8000/api/version", timeout=2) as r:
            return json.loads(r.read()).get("version") or "?"
    except urllib.error.HTTPError:
        return "?"   # algo responde, mas não é esta versão do programa (janela antiga?)
    except (urllib.error.URLError, OSError):
        return None  # porta livre
    except ValueError:
        return "?"


def main():
    other = running_version()
    if other:
        if other == "?":
            print("A porta 8000 já está em uso (talvez uma janela antiga deste programa ainda aberta).")
        else:
            print(f"O programa já está aberto em outra janela (versão {other}).")
        print("Para atualizar e evitar erros, feche TODAS as janelas pretas do programa e abra de novo.")
        webbrowser.open(URL)
        return

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
