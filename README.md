# Ragpi

Ragpi is an open-source AI assistant that answers questions using your documentation, GitHub issues, and READMEs. It combines LLMs with intelligent search to provide relevant, documentation-backed answers through a simple API. It supports multiple providers like OpenAI, Ollama, and Deepseek, and has built-in integrations with Discord and Slack. A web widget integration is also available to embed the assistant in your website.

[Documentation](https://docs.ragpi.io) | [API Reference](https://docs.ragpi.io/api)

## Key Features

- 📚 Builds knowledge bases from docs, GitHub issues and READMEs
- 🤖 Agentic RAG system for dynamic document retrieval
- 🔌 Supports OpenAI, Ollama, Deepseek & OpenAI-Compatible models
- 💬 Discord and slack integrations for community support
- 🚀 API-first design with Docker deployment

## Example Workflow

Here's a simple workflow to get started with Ragpi once it's deployed:

### 1. Set up a Source with a Connector

- Use the [`/sources`](https://docs.ragpi.io/api#tag/Sources/operation/create_source_sources_post) endpoint to configure a source with your chosen connector.
- Each connector type has its own configuration parameters.

Example payload using the Sitemap connector:

```json
{
  "name": "example-docs",
  "description": "Documentation for example project. It contains information about configuration, usage, and deployment.",
  "connector": {
    "type": "sitemap",
    "sitemap_url": "https://docs.example.com/sitemap.xml"
  }
}
```

### 2. Monitor Source Synchronization

- After adding a source, documents will be synced automatically. You can monitor the sync process through the [`/tasks`](https://docs.ragpi.io/api#tag/Tasks/operation/get_task_tasks__task_id__get) endpoint.

### 3. Chat with the AI Assistant

- Use the [`/chat`](https://docs.ragpi.io/api#tag/Chat/operation/chat_chat_post) endpoint to query the AI assistant using the configured sources:

  ```json
  {
    "sources": ["example-docs"],
    "messages": [
      { "role": "user", "content": "How do I deploy the example project?" }
    ]
  }
  ```

- You can also interact with the AI assistant through the [Discord](https://docs.ragpi.io/integrations/discord) or [Slack](https://docs.ragpi.io/integrations/slack) integration,
  or by embedding the [Web Widget](https://docs.ragpi.io/integrations/web-widget) in your website.

## Connectors

Ragpi supports the following connectors for building knowledge bases:

- **Documentation Website (Sitemap)**
- **GitHub Issues**
- **GitHub README Files**

[Explore connectors →](https://docs.ragpi.io/connectors)

## Providers

Ragpi supports the following LLM providers for generating responses and embeddings:

- **OpenAI** (default)
- **Ollama**
- **Deepseek**
- **OpenAI-compatible APIs**

[Configure providers →](https://docs.ragpi.io/providers/overview)

## Integrations

Ragpi supports the following integrations for interacting with the AI assistant:

- [**Discord**](https://docs.ragpi.io/integrations/discord)
- [**Slack**](https://docs.ragpi.io/integrations/slack)
- [**Web Widget**](https://docs.ragpi.io/integrations/web-widget)

## Contributing

Contributions to Ragpi are welcome! Please check out the [contributing guidelines](CONTRIBUTING.md) for more information.
