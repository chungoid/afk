# Analysis Agent – Iteration 2

## 1. Architecture & Data Flow

### Client / Trigger  
• HTTP endpoint, CLI, or a message on the `analysis.request` topic kicks off the workflow.

### Orchestrator (“Analysis Agent”)  
1. **Context Retrieval**  
   • Query Pinecone (or equivalent vector store) for similar past decisions and patterns  
   • Return top-K passages to feed into the prompt chain  
2. **Intent Extraction & Decomposition Prompt Chain**  
   • A multi-step chain calling the LLM via a small wrapper that handles prompt templates, temperature, and backoff:  
     1. Extract primary intent  
     2. Identify edge-cases and exceptions  
     3. Decompose into discrete task descriptions  
3. **Schema Validation**  
   • Use a canonical JSON Schema for `Task` objects  
   • Validate each generated task; on failure, re-prompt or emit an error  
4. **Publication**  
   • Assemble validated tasks into a batch  
   • Publish each to the `tasks.analysis` topic with metadata (request ID, timestamp)

### Persistence & Observability  
• Log full transcript of prompt chain, raw vs. validated outputs  
• Metrics: per-step latency, validation failure rate, queue lengths  
• Error handling: dead-letter topic for tasks that repeatedly fail schema validation  

---

## 2. Code Organization & Technology

### 2.1 Directory Layout
/src  
  /app  
    index.ts            # Bootstrap, DI container, HTTP listener or message consumer  
  /config  
    default.ts          # Env vars, Pinecone creds, LLM endpoint, topic names  
  /chain  
    chainManager.ts     # Orchestrates multi-step prompt chain  
    step1_intent.ts     # Intent-extraction prompt + wrapper  
    step2_edgecases.ts  # Edge-case enumeration  
    step3_decompose.ts  # Task decomposition prompts  
  /schema  
    task.schema.json    # JSON Schema for Task object  
  /validation  
    validator.ts        # AJV wrapper for schema enforcement  
  /vector  
    pineconeClient.ts   # Init Pinecone, upsert/query  
    retriever.ts        # Fetch related context documents  
  /publisher  
    mcpPublisher.ts     # Wrapper around MCP for `tasks.analysis` topic  
  /utils  
    logger.ts           # Structured logging  
    metrics.ts          # Prometheus metrics exporter  
  /tests  
    /unit               # Validator and chain-step mocks  
    /integration        # E2E: mock LLM + Pinecone + validate + publish  

### 2.2 Key Dependencies  
• OpenAI SDK (or internal LLM abstraction)  
• Pinecone SDK (or alternative vector DB client)  
• AJV (JSON Schema) or protobuf-js + generated TS types  
• Kafka or MCP’s built-in publisher (`mcp-use`)  
• Jest (unit) + supertest (integration)

### 2.3 Design Patterns  
• Dependency Injection (tsyringe or Inversify) for easy mocking  
• Hexagonal architecture: interchangeable adapters for prompting, retrieval, validation, publishing  
• Centralized error-handling middleware supporting retry and dead-letter  

---

## 3. Phased Rollout Plan & Milestones

### Phase 0: Initial Setup (1 day)  
• Scaffold repo / branch `analysis-agent/iteration-2`  
• Add basic service skeleton: config loader, logger, DI container, “hello world” endpoint or listener  

### Phase 1: Data Contracts (1–2 days)  
• Write `Task` JSON Schema (fields: id, title, description, dependencies, metadata)  
• (Optional) Define equivalent `.proto` and generate TS bindings  
• Add validator module + unit tests for schema enforcement  

### Phase 2: Vector DB Integration (2 days)  
• Init Pinecone client; write retriever to encode requirement and return nearest neighbors  
• Unit tests mocking Pinecone responses  
• Seed demo index with sample “past decisions”  

### Phase 3: Prompt Chain Implementation (3–4 days)  
• Implement `chainManager` calling step1, step2, step3 in sequence  
• Store prompt templates under `/prompts` with clear placeholders  
• Add retries, backoff and logging per step  
• Unit tests for each chain step with a mocked LLM client  

### Phase 4: Publisher & End-to-End Glue (2 days)  
• Implement `mcpPublisher` to send to `tasks.analysis` topic  
• Wire up orchestrator: on message/HTTP request → retrieve → chain → validate → publish  
• Integration test: stub MCP or Kafka and run full workflow  

### Phase 5: Hardening & Tests (2 days)  
• Add schema-validation test suite: invalid tasks emit meaningful errors  
• E2E tests: simulate edge-case requirements, assert correct decomposition  
• CI pipeline: lint, build, test, publish container or registry artifact  
• Add instrumentation: metrics, health endpoints  

### Phase 6: Documentation & Handoff (1 day)  
• Update README with setup, env vars, schema definitions  
• Add data-flow diagram in `/docs/analysis-agent.md`  
• Provide example curl/CLI invocation  

---

Total estimated effort: ~2 weeks for a single dedicated engineer or small team. This plan ensures strict data contracts, decoupled concerns, testability, and incremental scalability.