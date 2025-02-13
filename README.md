# Ragpi

[![Documentation](https://img.shields.io/badge/docs-ragpi.io-blue)](https://docs.ragpi.io)

Ragpi is an open-source AI assistant that answers technical questions using your documentation, GitHub issues, and READMEs. It combines LLMs with intelligent search to provide accurate, context-aware answers through a simple API.

## Key Features

- 📚 Builds knowledge bases from docs, GitHub issues and READMEs
- 🤖 Agentic RAG system for dynamic document retrieval
- 🔌 Supports OpenAI, Ollama, Deepseek & OpenAI-Compatible models
- 💬 Discord integration for community support
- 🚀 API-first design with Docker deployment

## Quick Start

### 1. Clone and configure:

Clone the repository and create a `.env` file with your OpenAI key:

```bash
git clone https://github.com/ragpi/ragpi.git
cd ragpi
cp .env.example .env
# Edit .env with your OpenAI key
```

### 2. Start services:

Start Ragpi using Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 3. Add your first source:

Use the Sitemap Connector to create a new source:

```bash
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "example-docs",
    "description": "Documentation for example project",
    "connector": {
      "type": "sitemap",
      "sitemap_url": "https://your-docs.com/sitemap.xml"
    }
  }'
```

### 4. Monitor Synchronization Progress:

Get the `task_id` from the response of the above command and monitor the source synchronization progress:

```bash
curl http://localhost:8000/tasks/{task_id}
```

### 5. Ask questions:

Once the source is synchronized, you can ask questions:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": "How do I configure X?"
    }]
  }'
```

## Connectors

Ragpi supports multiple connectors to fetch data from various sources:

- **Website Sitemap**
- **GitHub Issues**
- **GitHub README Files**

[Explore connectors →](https://docs.ragpi.io/connectors)

## Providers

Ragpi supports multiple LLM providers for generating responses and embeddings:

- **OpenAI** (default)
- **Ollama**
- **Deepseek**
- **OpenAI-compatible APIs**

[Configure providers →](https://docs.ragpi.io/providers/overview)

## Integrations

- [**Discord**](https://github.com/ragpi/ragpi-discord)

[Set up Discord integration →](https://docs.ragpi.io/integrations/discord)

## Documentation

Full documentation available at [docs.ragpi.io](https://docs.ragpi.io).
