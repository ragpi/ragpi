# Contributing to Ragpi

Thank you for your interest in contributing to Ragpi! The following guidelines will help you get started with contributing effectively.

## How to Contribute

### Reporting Bugs

If you encounter a bug, please [create an issue](https://github.com/ragpi/ragpi/issues/new) on GitHub with the following information:

- A clear and descriptive title.
- A description of the steps to reproduce the issue.
- Any relevant logs or other information that can help us understand the problem.

### Suggesting Features

Feature suggestions are welcome! If you have an idea to improve Ragpi, please [open an issue](https://github.com/ragpi/ragpi/issues/new) with the following details:

- A clear and descriptive title.
- A detailed description of the proposed feature.
- Any additional context or examples that would help understand the feature.

### Submitting Changes

1. **Follow the development setup instructions** to set up your local environment.
2. **Create a new branch** for your changes (use a descriptive name).
3. **Make your changes** and commit them with clear and descriptive messages.
4. **Push your changes** to your forked repository.
5. **Open a pull request** to the `main` branch of the original repository.

Please ensure your pull request includes a clear description of the changes and the problem they solve.

## Development Setup

This section provides detailed instructions for setting up your development environment for Ragpi.

### Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.11** (required version)
- **[Poetry](https://python-poetry.org/docs/)** for dependency management
- **Docker** and **Docker Compose** for running required services
- **Git** for version control

### Step 1: Clone the Repository

[Fork the Ragpi repository](https://github.com/ragpi/ragpi/fork) on GitHub, then clone your fork locally:

```bash
git clone https://github.com/<your-username>/ragpi.git
cd ragpi
```

### Step 2: Set Up Python Environment

Ensure you're using Python 3.11, then install dependencies using Poetry. This command will create a virtual environment and install all required packages:

```bash
poetry install
```

To install pre-commit hooks, run the following command:

```bash
poetry run pre-commit install
```

### Step 3: Configure Environment Variables

Copy the example environment file and open it for editing:

```bash
cp .env.example .env
```

Add your `OPENAI_API_KEY` to the `.env` if using openai as your chat and embedding provider, otherwise [configure the provider](https://docs.ragpi.io/providers/overview) you want to use.

### Step 4: Start the Development Services

Start all required services using Docker Compose:

```bash
docker compose up -d --build
```

This command starts:

- Redis on port 6378
- PostgreSQL with pgvector extension on port 5433
- FastAPI application on port 8000
- Celery worker for background tasks

### Running Tests

To run the test suite, use the following command:

```bash
poetry run pytest
```

### Stopping the Environment

To stop the development services:

```bash
docker compose down
```

To completely clean up (removing volumes):

```bash
docker compose down -v
```
