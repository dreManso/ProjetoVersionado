# Regras do projeto

- A cada alteração no app, atualize a versão em `app/version.py` e registre o que mudou no topo do `CHANGELOG.md` (com a data). Mencione a nova versão na mensagem do commit.
  - X.0.0 mudança grande · x.Y.0 função nova · x.y.Z correção/ajuste.
- A versão aparece no menu do app (vem de `/api/version`). Não escreva o número em outros lugares.
- Textos do app e do changelog em português, para o usuário final (dono do restaurante).
- Antes de publicar: `python -m pytest -q`.
