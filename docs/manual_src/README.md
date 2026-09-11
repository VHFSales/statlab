# Fontes do manual em PDF

O manual de instruções está em `docs/manual_statlab.pdf`. Ele é gerado por scripts
puros de Python (sem dependências externas), para funcionar em qualquer ambiente.

- `pdf_writer.py` — gerador de PDF mínimo (stdlib): estilos, quebra de linha e
  paginação, com fontes padrão Helvetica/Courier (WinAnsiEncoding).
- `build_manual.py` — conteúdo do manual e montagem do PDF.

## Regenerar o PDF

```
python docs/manual_src/build_manual.py
```

Isso reescreve `docs/manual_statlab.pdf`.
