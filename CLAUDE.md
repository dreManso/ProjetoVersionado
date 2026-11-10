# Regras do projeto

- A cada alteração no app, atualize a versão em `app/version.py` e registre o que mudou no topo do `CHANGELOG.md` (com a data). Mencione a nova versão na mensagem do commit.
  - X.0.0 mudança grande · x.Y.0 função nova · x.y.Z correção/ajuste.
- A versão aparece no menu do app (vem de `/api/version`). Não escreva o número em outros lugares.
- Textos do app e do changelog em português, para o usuário final (dono do restaurante).
- Antes de publicar: `python -m pytest -q`.
- O app instalado se atualiza sozinho ao abrir (`app/updater.py`, chamado pelo `run.py`), comparando `app/version.py` com o publicado nas branches de `BRANCHES`. Por isso a versão PRECISA subir a cada alteração, senão o usuário não recebe a mudança.
- O updater não substitui `*.db` nem `*.bat`. Não dependa de mudanças em `Abrir Cozinha.bat`: ele não é atualizado automaticamente.
