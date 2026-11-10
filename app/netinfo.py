"""Endereço do computador na rede local, para abrir o app no celular (mesmo Wi-Fi)."""
import socket

PORT = 8000


def lan_ip():
    """IP do computador na rede local (ex.: 192.168.0.15). None se não encontrar."""
    try:
        # não envia nada: só pergunta ao sistema qual placa de rede seria usada
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            return None
    return None if ip.startswith("127.") else ip


def lan_url():
    ip = lan_ip()
    return f"http://{ip}:{PORT}" if ip else None
