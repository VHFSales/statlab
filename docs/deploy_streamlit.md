# Publicar o StatLab como link (Streamlit Community Cloud)

O StatLab pode ser publicado gratuitamente no **Streamlit Community Cloud**,
gerando uma URL pública (ex.: `https://statlab-....streamlit.app`) que qualquer
pessoa abre no navegador — sem instalar nada.

O repositório já está preparado para isso:
- `streamlit_app.py` (na raiz) — ponto de entrada que o Streamlit Cloud detecta.
- `requirements.txt` — dependências (streamlit, pandas, matplotlib, openpyxl).
- `.streamlit/config.toml` — configuração/tema.
- `runtime.txt` — fixa o Python 3.11.

## Passo a passo (leva ~3 minutos, feito por você)

1. Acesse **https://share.streamlit.io** e clique em **Sign in** (entre com a sua
   conta do **GitHub** — a mesma dona do repositório, `VHFSales`).
2. Autorize o Streamlit a acessar seus repositórios do GitHub (só na primeira vez).
3. Clique em **Create app** (ou **New app**) → **Deploy a public app from GitHub**.
4. Preencha:
   - **Repository:** `VHFSales/statlab`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
5. Clique em **Deploy!**

A primeira publicação instala as dependências e leva 1–3 minutos. Ao terminar, você
recebe a URL pública do app. Toda vez que você fizer um push no branch `main`, o
Streamlit Cloud **atualiza o app automaticamente**.

## Observações

- **Gratuito** para apps públicos. Requer apenas a sua conta GitHub.
- Se quiser um endereço personalizado, o Streamlit permite escolher o subdomínio
  (`https://<nome-escolhido>.streamlit.app`) na hora do deploy.
- Recursos que gravam arquivos no servidor (ex.: gerar um `.xlsx` no disco) se
  comportam de forma efêmera na nuvem; o download pelo navegador (CSV/HTML/relatório)
  funciona normalmente.
