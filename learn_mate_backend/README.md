# Learn Mate Backend

Learn Mate后端服务 - 基于FastAPI和LangGraph构建的AI学习助手。提供智能学习对话、内容分析和个性化学习建议功能。

## 🌟 Features

- **Production-Ready Architecture**

  - FastAPI for high-performance async API endpoints
  - LangGraph integration for AI agent workflows
  - Langfuse for LLM observability and monitoring
  - Structured logging with environment-specific formatting
  - Rate limiting with configurable rules
  - PostgreSQL for data persistence
  - Docker and Docker Compose support
  - Prometheus metrics and Grafana dashboards for monitoring

- **Security**

  - JWT-based authentication
  - Session management
  - Input sanitization
  - CORS configuration
  - Rate limiting protection

- **Developer Experience**

  - Environment-specific configuration
  - Comprehensive logging system
  - Clear project structure
  - Type hints throughout
  - Easy local development setup

- **Model Evaluation Framework**
  - Automated metric-based evaluation of model outputs
  - Integration with Langfuse for trace analysis
  - Detailed JSON reports with success/failure metrics
  - Interactive command-line interface
  - Customizable evaluation metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL ([see Database setup](#database-setup))
- Docker and Docker Compose (optional)

### Environment Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

2. Create and activate a virtual environment:

```bash
uv sync
```

3. Copy the example environment file:

```bash
cp .env.example .env.[development|staging|production] # e.g. .env.development
```

4. Update the `.env` file with your configuration (see `.env.example` for reference)

### Database setup

1. Create a PostgreSQL database (e.g Supabase or local PostgreSQL)
2. Update the database connection string in your `.env` file:

```bash
POSTGRES_URL="postgresql://:your-db-password@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB"
```

- You don't have to create the tables manually, the ORM will handle that for you.But if you faced any issues,please run the `schemas.sql` file to create the tables manually.

### Running the Application

#### Local Development

1. Install dependencies:

```bash
uv sync
```

2. Run the application:

```bash
make [dev|staging|production] # e.g. make dev
```

1. Go to Swagger UI:

```bash
http://localhost:8000/docs
```

#### Using Docker

1. Build and run with Docker Compose:

```bash
make docker-build-env ENV=[development|staging|production] # e.g. make docker-build-env ENV=development
make docker-run-env ENV=[development|staging|production] # e.g. make docker-run-env ENV=development
```

2. Access the monitoring stack:

```bash
# Prometheus metrics
http://localhost:9090

# Grafana dashboards
http://localhost:3000
Default credentials:
- Username: admin
- Password: admin
```

The Docker setup includes:

- FastAPI application
- PostgreSQL database
- Prometheus for metrics collection
- Grafana for metrics visualization
- Pre-configured dashboards for:
  - API performance metrics
  - Rate limiting statistics
  - Database performance
  - System resource usage

## 📊 Model Evaluation

The project includes a robust evaluation framework for measuring and tracking model performance over time. The evaluator automatically fetches traces from Langfuse, applies evaluation metrics, and generates detailed reports.

### Running Evaluations

You can run evaluations with different options using the provided Makefile commands:

```bash
# Interactive mode with step-by-step prompts
make eval [ENV=development|staging|production]

# Quick mode with default settings (no prompts)
make eval-quick [ENV=development|staging|production]

# Evaluation without report generation
make eval-no-report [ENV=development|staging|production]
```

### Evaluation Features

- **Interactive CLI**: User-friendly interface with colored output and progress bars
- **Flexible Configuration**: Set default values or customize at runtime
- **Detailed Reports**: JSON reports with comprehensive metrics including:
  - Overall success rate
  - Metric-specific performance
  - Duration and timing information
  - Trace-level success/failure details

### Customizing Metrics

Evaluation metrics are defined in `evals/metrics/prompts/` as markdown files:

1. Create a new markdown file (e.g., `my_metric.md`) in the prompts directory
2. Define the evaluation criteria and scoring logic
3. The evaluator will automatically discover and apply your new metric

### Viewing Reports

Reports are automatically generated in the `evals/reports/` directory with timestamps in the filename:

```
evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json
```

Each report includes:

- High-level statistics (total trace count, success rate, etc.)
- Per-metric performance metrics
- Detailed trace-level information for debugging

## 🔧 Configuration

The application uses a flexible configuration system with environment-specific settings:

- `.env.development`
-
