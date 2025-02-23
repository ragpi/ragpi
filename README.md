# Ragpi

[Documentation](https://docs.ragpi.io) | [API Reference](https://docs.ragpi.io/api)

Ragpi is an open-source AI assistant that answers questions using your documentation, GitHub issues, and READMEs. It combines LLMs with intelligent search to provide relevant, documentation-backed answers through a simple API. It supports multiple providers like OpenAI, Ollama, and Deepseek, and has built-in integrations with Discord and Slack.

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/7ihedX?referralCode=Z4YGGz)

## Key Features

- 📚 Builds knowledge bases from docs, GitHub issues and READMEs
- 🤖 Agentic RAG system for dynamic document retrieval
- 🔌 Supports OpenAI, Ollama, Deepseek & OpenAI-Compatible models
- 💬 Discord integration for community support
- 🚀 API-first design with Docker deployment

## Quick Start

This is a quick guide to get you started with Ragpi locally. To deploy Ragpi to a production environment, refer to the [Deployment Documentation](https://docs.ragpi.io/deployment) to learn more about different deployment options.

### 1. Clone and configure:

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/ragpi/ragpi.git
cd ragpi
```

Copy the example environment file and open it for editing:

```bash
cp .env.example .env
```

Configure the essential environment variables in `.env`:

```env
# Add your OpenAI API key
OPENAI_API_KEY=your_api_key_here

# Optional: Add your GtiHub Token if using a GitHub connector
GITHUB_TOKEN=your_github_token

# Optional: Add API authentication
RAGPI_API_KEY=your_secret_api_key
```

**Note:** If you would like to enable API authentication, set the `RAGPI_API_KEY` environment variable to a [self-generated key](https://docs.ragpi.io/configuration#generating-an-api-key). Include this key in the `x-api-key` header for all requests.

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

- **Documentation Website (Sitemap)**
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

Ragpi supports integrations with popular platforms like Discord and Slack:

- [**Discord**](https://docs.ragpi.io/integrations/discord)
- [**Slack**](https://docs.ragpi.io/integrations/slack)
