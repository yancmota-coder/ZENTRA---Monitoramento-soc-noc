# ZENTRA NOC v0.3.0 — Hydra UI

Esta versão altera **somente o frontend** para aplicar a identidade visual do HTML de referência:
- fundo cyberpunk com grade, brilho ambiente e scanlines;
- painéis HUD translúcidos com bordas neon;
- identidade ZENTRA com logo SVG animado;
- tipografia Orbitron, Inter e JetBrains Mono;
- navegação e componentes responsivos;
- estados reais de integração, sem inserir métricas fictícias.

## Backend
O diretório `backend/` foi preservado sem alterações. Endpoints, integração Zabbix, configurações e dependências permanecem os mesmos da versão v0.3.0 recebida.

## Instalação
Substitua a pasta do projeto pela versão deste pacote ou copie apenas `frontend/` sobre seu frontend atual.

Na pasta `frontend/`:
```bash
npm install
cp .env.example .env
npm run dev -- --host 0.0.0.0
```

Configure `VITE_API_BASE_URL` no `frontend/.env` para o endereço da API ZENTRA (por exemplo `http://192.168.56.10:8000`).

## Observação de integridade
A interface consome os mesmos endpoints `/api/*` já existentes. O redesenho não implementa novas integrações nem altera o comportamento do backend. A compilação de produção não foi executada neste ambiente porque as dependências npm não estavam instaladas; valide com `npm install` e `npm run build` na VM.
