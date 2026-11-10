"""
Atualização automática a partir do GitHub (repositório público).

Ao abrir o programa (run.py), compara a versão instalada com a publicada.
Se houver versão mais nova, baixa o pacote e substitui SÓ os arquivos do
programa. Nunca toca nos dados (*.db), no relatório de importação nem no
atalho "Abrir Cozinha.bat" (ele pode estar em execução nessa hora).
Sem internet, segue com a versão instalada.
"""
import io
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "dreManso/ProjetoVersionado"
BRANCHES = ["claude/restaurant-dish-pricing-zb0wta", "main"]
ROOT = Path(__file__).resolve().parent.parent
PROTECTED_SUFFIXES = {".db", ".db-journal", ".db-wal", ".db-shm", ".bat"}
PROTECTED_NAMES = {"relatorio_importacao.txt"}
CHECK_TIMEOUT = 5
DOWNLOAD_TIMEOUT = 60


def _get(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "cozinha-updater"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_version(text: str):
    m = re.search(r'__version__\s*=\s*"(\d+(?:\.\d+)*)"', text)
    return m.group(1) if m else None


def as_tuple(v: str):
    return tuple(int(x) for x in v.split("."))


def local_version() -> str:
    return parse_version((ROOT / "app" / "version.py").read_text(encoding="utf-8")) or "0"


def remote_latest():
    """(versão, branch) mais nova publicada, ou None se não conseguir consultar."""
    best = None
    for branch in BRANCHES:
        try:
            raw = _get(f"https://raw.githubusercontent.com/{REPO}/{branch}/app/version.py", CHECK_TIMEOUT)
        except Exception:
            continue
        v = parse_version(raw.decode("utf-8", "replace"))
        if v and (best is None or as_tuple(v) > as_tuple(best[0])):
            best = (v, branch)
    return best


def changes_since(changelog: str, old: str) -> list:
    """Linhas do CHANGELOG das versões mais novas que `old`."""
    out, keep = [], False
    for line in changelog.splitlines():
        m = re.match(r"##\s+(\d+(?:\.\d+)*)", line)
        if m:
            keep = as_tuple(m.group(1)) > as_tuple(old)
            if keep:
                out.append(line.lstrip("# ").strip())
            continue
        if keep and line.strip().startswith("-"):
            out.append("   " + line.strip())
    return out


def apply_update(branch: str) -> list:
    """Baixa o pacote da branch e grava os arquivos alterados. Retorna os arquivos trocados."""
    data = _get(f"https://github.com/{REPO}/archive/refs/heads/{branch}.zip", DOWNLOAD_TIMEOUT)
    req_file = ROOT / "requirements.txt"
    req_before = req_file.read_bytes() if req_file.exists() else b""
    changed = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        prefix = names[0].split("/")[0] + "/"
        for name in names:
            if name.endswith("/") or not name.startswith(prefix):
                continue
            rel = Path(name[len(prefix):])
            if rel.is_absolute() or ".." in rel.parts:
                continue
            if rel.suffix.lower() in PROTECTED_SUFFIXES or rel.name in PROTECTED_NAMES:
                continue
            content = z.read(name)
            dest = ROOT / rel
            if dest.exists() and dest.read_bytes() == content:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".novo")
            tmp.write_bytes(content)
            os.replace(tmp, dest)
            changed.append(str(rel))
    if req_file.exists() and req_file.read_bytes() != req_before:
        print("Instalando componentes novos...")
        subprocess.call([sys.executable, "-m", "pip", "install", "-q", "-r", str(req_file)])
    return changed


def check_and_update() -> bool:
    """Confere e aplica atualização. Retorna True se o programa foi atualizado."""
    current = local_version()
    print(f"Versão instalada: {current}. Procurando atualizações...")
    latest = remote_latest()
    if latest is None:
        print("Não consegui verificar (sem internet?). Abrindo a versão instalada.")
        return False
    version, branch = latest
    if as_tuple(version) <= as_tuple(current):
        print("Você já está na versão mais nova.")
        return False
    print(f"Nova versão {version} disponível. Atualizando...")
    try:
        apply_update(branch)
    except Exception as e:  # nunca impedir o programa de abrir
        print(f"Não foi possível atualizar agora ({e}). Abrindo a versão instalada.")
        return False
    try:
        notes = changes_since((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), current)
        if notes:
            print("O que mudou:")
            print("\n".join("  " + n for n in notes))
    except Exception:
        pass
    print(f"Atualizado para a versão {version}.\n")
    return True
