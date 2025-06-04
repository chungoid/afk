# Analysis Agent

A hardened, production-ready pipeline for requirement analysis, task decomposition, validation, and publication.

## Overview

This repository provides a fully operationalized Analysis Agent that takes raw requirements, retrieves relevant context via RAG, generates intent and decomposed tasks through an LLM prompt chain, validates task schemas, and publishes them to a messaging layer.

## Features

• RAG context retrieval with vector store (Pinecone)  
• Multi-step LLM prompting for intent extraction and task decomposition  
• JSON Schema and Pydantic validation  
• Robust publisher with retries and metrics hooks  
• CLI entrypoint with `python -m orchestrator run_pipeline`  
• Comprehensive unit and integration tests  
• CI/CD pipeline with schema checks, linting, and coverage  
• Modular, extensible architecture

## Getting Started

### Prerequisites

• Python 3.9+  
• API keys for OpenAI (or other LLM service)  
• Pinecone API key and environment  
• Messaging layer credentials (MCP)  

### Installation

git clone <repo_url>  
cd <repo_root>  
python -m venv venv  
source venv/bin/activate  
pip install -r requirements.txt  

### Configuration

Create a `.env` file or export environment variables:

OPENAI_API_KEY=your_openai_key  
PINECONE_API_KEY=your_pinecone_key  
PINECONE_ENVIRONMENT=your_pinecone_env  
MCP_API_KEY=your_mcp_key  
MCP_TOPIC=tasks.analysis

## Project Structure

Run `scripts/print_tree.sh` to generate `repo_structure.txt`. Excerpt:

.
├── prompts
│   ├── prompt_templates
│   │   ├── intent_extraction.j2
│   │   └── decomposition_step.j2
│   └── chain.py
├── schemas
│   ├── task.schema.json
│   └── prompt_chain.schema.json
├── validators
│   ├── __init__.py
│   ├── validate.py
│   └── models.py
├── orchestrator
│   ├── __main__.py
│   ├── run_pipeline.py
│   └── rag_retriever.py
├── publishers
│   └── mcp_publisher.py
├── scripts
│   └── print_tree.sh
├── tests
│   ├── validators_test.py
│   ├── prompt_chain_test.py
│   ├── rag_retriever_test.py
│   └── orchestrator_flow_test.py
├── docs
│   ├── ARCHITECTURE.md
│   ├── USAGE.md
│   ├── TESTING.md
│   └── Schemas.md
├── .gitignore
└── README.md

## Usage

Run the pipeline:

python -m orchestrator run_pipeline --input requirements.txt

Flags:

--input  Path to a file with raw requirement text (defaults to stdin)  
--output File to write JSON tasks (defaults to stdout)  
--verbose Enable debug logging  

### Example

cat requirement.txt | python -m orchestrator run_pipeline > tasks.json

## Testing

Install dev dependencies:

pip install -r requirements-dev.txt

Run tests and schema validation:

pytest --schema-validation --cov=.

## CI/CD

A GitHub Actions workflow runs on each PR:

1. Checkout & print tree  
2. Install dependencies  
3. Lint (black, isort, flake8)  
4. Run pytest with schema plugin  
5. Smoke-test orchestrator with fixtures  
6. Upload coverage report

## Contributing

1. Fork the repo  
2. Create a feature branch  
3. Write code and tests  
4. Ensure `scripts/print_tree.sh` output is up to date  
5. Submit a PR and pass CI checks

## License

MIT License. See LICENSE file for details.