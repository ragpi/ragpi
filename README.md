# Ragpi

Ragpi is an API-first AI assistant that leverages LLMs to search and answer questions using technical sources. It builds knowledge bases from documentation websites, GitHub Issues, and repository README files, storing them in a vector database for efficient retrieval. Using an Agentic RAG approach, it dynamically retrieves relevant documents to answer queries through its REST API.

📚 [API Reference](https://docs.ragpi.io)

## Table of Contents

- [Features](#features)
- [Example Workflow](#example-workflow)
- [LLM Providers](#llm-providers)
- [Source Connectors](#source-connectors)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)

## Features

- **API-First Design** - REST API for all functionality
- **Agentic RAG System** - Dynamic document retrieval based on queries
- **Hybrid Search** - Combines semantic and keyword search using Reciprocal Rank Fusion (RRF)
- **Flexible Connectors** - Support for docs, GitHub issues, and READMEs
- **LLM Integration** - Response generation using selected LLM providers
- **Observability** - Basic OpenTelemetry tracing support

## Example Workflow

1. **Set up a Source with a Connector**:

   - Use the [/sources](https://docs.ragpi.io/#tag/sources/POST/sources) endpoint to configure a source with your chosen connector.
   - Each connector type has its own configuration parameters.

   Example using the Sitemap connector:

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

2. **Monitor Source Synchronization**:

   - After adding a source, documents will be synced automatically. You can monitor the sync process through the [/tasks](https://docs.ragpi.io/#tag/tasks/GET/tasks/{task_id}) endpoint.

3. **Chat with the AI Assistant**:

   - Use the [/chat](https://docs.ragpi.io/#tag/chat/POST/chat) endpoint to query the AI assistant using the configured sources.
   - If no sources are specified in the payload, all available sources will be used.
   - Example payload:
     ```json
     {
       "sources": ["my-docs"],
       "messages": [
         { "role": "user", "content": "What are the deployment options?" }
       ]
     }
     ```

## LLM Providers

Ragpi integrates with the following providers:

### Chat Services

- OpenAI (default, requires `OPENAI_API_KEY`)
- Ollama (requires `OLLAMA_BASE_URL`)

### Embedding Services

- OpenAI (default, requires `OPENAI_API_KEY`)
- Ollama (requires `OLLAMA_BASE_URL`)

Configure providers using environment variables:

```env
CHAT_PROVIDER=openai|ollama
EMBEDDING_PROVIDER=openai|ollama
```

## Source Connectors

Ragpi uses a flexible connector-based architecture to extract and process documents from various sources. Each connector is designed to handle specific types of data sources and implements common chunking and processing logic.

### Available Connectors

- **Sitemap Connector**:

  - Extracts and processes pages from website sitemaps
  - Supports regex patterns for including/excluding URLs
  - Respects robots.txt directives
  - Converts HTML content to Markdown for processing

- **GitHub Issues Connector**:

  - Fetches and analyzes issues and comments from GitHub repositories
  - Supports filtering by issue state (open/closed)
  - Can include/exclude based on labels
  - Configurable age limit for issues

- **GitHub README Connector**:
  - Retrieves README files from repositories
  - Can fetch from root and specified subdirectories
  - Supports branch/ref selection
  - Processes multiple README files as needed

## Deployment

Ragpi supports several deployment options to suit your infrastructure and requirements:

### 1. Local Docker Deployment

Clone the repository:

```bash
git clone https://github.com/ragpi/ragpi.git
cd ragpi
```

Before running the production `docker-compose.prod.yml` file locally, configure the `.env` file with the necessary environment variables:

```bash
cp .env.example .env
# Edit the .env file to set your API keys and other configuration
```

Then, run the following command:

```bash
docker compose -f docker-compose.prod.yml --profile internal-redis up -d
```

### 2. Remote Docker Deployment

**Note:** Ensure that the necessary configuration and security measures are implemented on your remote server to protect the deployment environment. Additionally, securely configure environment variables (e.g., API keys, tokens) on the server. You can use the `.env` file or set them directly in the server's environment using a method that best suits your security requirements.

Clone the repository to your remote server (VM, VPS, or similar):

```bash
git clone https://github.com/ragpi/ragpi.git
cd ragpi
```

Use the production `docker-compose.prod.yml` file:

```bash
docker compose -f docker-compose.prod.yml --profile internal-redis up -d
```

### 3. API-Only Deployment

For users looking to simplify their deployment by avoiding the need to deploy Celery workers alongside the API, this option provides a streamlined workflow:

1. **Redis-Stack Server Setup**:

   - Use a Redis Stack server instance with data persistence. You can either:
     - Obtain a managed instance from Redis Cloud, or
     - Deploy and manage your own Redis stack server instance.
   - Note down the `REDIS_URL` for connecting to the Redis instance.

2. **Deploy API**:

   - Deploy the API using the [ragpi/ragpi](https://hub.docker.com/r/ragpi/ragpi) Docker image.
   - Set the `REDIS_URL` environment variable to point to your Redis instance.
   - Ensure the `WORKERS_ENABLED` environment variable is set to `False` in the deployed environment to disable endpoints requiring Celery workers.
   - The deployed API will connect to the Redis instance for all operations.

3. **Manage Sources Locally**:

   - Clone the repository to your local machine:
     ```bash
     git clone https://github.com/ragpi/ragpi.git
     cd ragpi
     ```
   - Set up the environment variables in a `.env` file:
     ```bash
     cp .env.example .env
     # Edit the .env file to include the following:
     REDIS_URL=<your-redis-url>
     WORKERS_ENABLED=True
     ```
   - Start the local API and workers using Docker Compose:
     ```bash
     docker compose -f docker-compose.prod.yml up -d
     ```
   - Interact with the local API to:
     - Create new sources using the `/sources` endpoint.
     - Update existing sources as needed.

4. **Accessing Sources**:
   - Sources created or updated locally will be immediately available to the production API through the shared Redis instance.

### 4. Custom Deployment

Supports deployment on Kubernetes or other container orchestration platforms using the [ragpi/ragpi](https://hub.docker.com/r/ragpi/ragpi) Docker image. Configure components independently based on your infrastructure needs. The Docker image contains both the API service and worker components, which can be controlled via environment variables.

For reference on how to configure the API and worker services, see the service definitions in `docker-compose.prod.yml` in the repository root.

## Environment Variables

### Core Configuration

| Variable          | Description                                     | Default                  | Notes                                                                             |
| ----------------- | ----------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------- |
| `API_KEYS`        | Comma-separated list of API keys for access     | None                     | If not set, API authentication will be disabled. Example format: `key1,key2,key3` |
| `REDIS_URL`       | Redis connection URL for storage and task queue | `redis://localhost:6379` | Default works for local Redis deployments                                         |
| `WORKERS_ENABLED` | Enable/disable background workers               | `True`                   | When disabled, endpoints requiring Celery workers will return 503 errors          |

### Provider Configuration

| Variable             | Description                                             | Default  | Notes                                |
| -------------------- | ------------------------------------------------------- | -------- | ------------------------------------ |
| `CHAT_PROVIDER`      | Chat service provider. Options: `openai`, `ollama`      | `openai` | -                                    |
| `EMBEDDING_PROVIDER` | Embedding service provider. Options: `openai`, `ollama` | `openai` | -                                    |
| `OLLAMA_BASE_URL`    | Base URL for Ollama provider                            | None     | Required if using Ollama as provider |
| `OPENAI_API_KEY`     | API key for OpenAI services                             | None     | Required if using OpenAI as provider |

### Application Settings

| Variable                  | Description                                                             | Default |
| ------------------------- | ----------------------------------------------------------------------- | ------- |
| `API_NAME`                | Name of the API service                                                 | `Ragpi` |
| `TASK_RETENTION_DAYS`     | Number of days to retain task history                                   | `7`     |
| `LOG_LEVEL`               | Logging level. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO`  |
| `USER_AGENT`              | User agent string for HTTP requests                                     | `Ragpi` |
| `MAX_CONCURRENT_REQUESTS` | Maximum number of concurrent requests                                   | `10`    |

### Model Settings

| Variable               | Description                                | Default                  | Notes                                                                                   |
| ---------------------- | ------------------------------------------ | ------------------------ | --------------------------------------------------------------------------------------- |
| `DEFAULT_CHAT_MODEL`   | Default model for chat interactions        | `gpt-4o-mini`            | -                                                                                       |
| `EMBEDDING_MODEL`      | Model used for embeddings                  | `text-embedding-3-small` | When changing this, ensure `EMBEDDING_DIMENSIONS` matches the model's output dimensions |
| `EMBEDDING_DIMENSIONS` | Dimensions for embedding vectors           | `1536`                   | Must match the selected embedding model's output dimensions                             |
| `BASE_SYSTEM_PROMPT`   | Default system prompt for the AI assistant | _See below_              | -                                                                                       |

### Chat Settings

| Variable              | Description                                     | Default |
| --------------------- | ----------------------------------------------- | ------- |
| `CHAT_HISTORY_LIMIT`  | Maximum number of messages in chat history      | `20`    |
| `MAX_CHAT_ITERATIONS` | Maximum steps allowed for generating a response | `5`     |

### Document Processing

| Variable                   | Description                                         | Default                                | Notes                                                       |
| -------------------------- | --------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------- |
| `DOCUMENT_STORE_NAMESPACE` | Namespace for document storage                      | `document_store`                       | -                                                           |
| `DOCUMENT_UUID_NAMESPACE`  | UUID namespace for document IDs                     | `ee747eb2-fd0f-4650-9785-a2e9ae036ff2` | -                                                           |
| `CHUNK_SIZE`               | Size of document chunks for processing (in tokens)  | `512`                                  | -                                                           |
| `CHUNK_OVERLAP`            | Overlap size between document chunks (in tokens)    | `50`                                   | -                                                           |
| `DOCUMENT_SYNC_BATCH_SIZE` | Number of documents processed per batch during sync | `500`                                  | Controls batch size when adding documents to document store |

### GitHub Integration

| Variable             | Description                             | Default      | Notes                                 |
| -------------------- | --------------------------------------- | ------------ | ------------------------------------- |
| `GITHUB_TOKEN`       | GitHub token for accessing repositories | None         | Required when using GitHub connectors |
| `GITHUB_API_VERSION` | GitHub API version                      | `2022-11-28` | -                                     |

### OpenTelemetry Settings

| Variable                      | Description                     | Default |
| ----------------------------- | ------------------------------- | ------- |
| `OTEL_ENABLED`                | Enable/disable OpenTelemetry    | `False` |
| `OTEL_SERVICE_NAME`           | Service name for OpenTelemetry  | `ragpi` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry exporter endpoint | None    |
| `OTEL_EXPORTER_OTLP_HEADERS`  | OpenTelemetry exporter headers  | None    |

When enabled, Ragpi provides basic tracing capabilities through OpenTelemetry instrumentation. This includes automatic tracing of FastAPI endpoints and OpenAI/Ollama API calls, with spans exported to the endpoint specified in `OTEL_EXPORTER_OTLP_ENDPOINT`.

### Default System Prompt

The default value for `BASE_SYSTEM_PROMPT` is:

```
You are an AI assistant specialized in retrieving and synthesizing technical information to provide relevant answers to queries.
```
