import 'dotenv/config';
import path from 'path';
import config from './config/default.json';
import { Orchestrator } from './agent/orchestrator';
import { LLMClient } from './services/llmClient';
import { VectorStore } from './services/vectorStore';
import { SchemaValidator } from './services/schemaValidator';
import { Publisher } from './services/publisher';

async function main() {
  try {
    // Initialize LLM client
    const llmClient = new LLMClient({
      apiKey: process.env.OPENAI_API_KEY || config.llm.apiKey,
      model: config.llm.model,
      temperature: config.llm.temperature,
      maxTokens: config.llm.maxTokens
    });

    // Initialize Vector Store
    const vectorStore = new VectorStore({
      apiKey: process.env.PINECONE_API_KEY || config.pinecone.apiKey,
      environment: config.pinecone.environment,
      indexName: config.pinecone.indexName
    });
    await vectorStore.init();

    // Initialize Schema Validator
    const schemaPath = path.resolve(__dirname, 'config', 'schema', 'task.schema.json');
    const schemaValidator = new SchemaValidator(schemaPath);

    // Initialize Publisher
    const publisher = new Publisher({
      url: process.env.MCP_URL || config.mcp.url,
      topic: config.mcp.topic || 'tasks.analysis'
    });
    await publisher.init();

    // Create Orchestrator
    const orchestrator = new Orchestrator(llmClient, vectorStore, schemaValidator, publisher, {
      ragContextSize: config.rag?.contextSize,
      ragTopK: config.rag?.topK
    });

    // Read requirement from CLI args
    const requirement = process.argv.slice(2).join(' ');
    if (!requirement) {
      console.error('Error: No requirement provided. Please pass a requirement string as an argument.');
      process.exit(1);
    }

    // Run the analysis agent
    await orchestrator.run(requirement);
    console.log('Tasks successfully published to topic:', publisher.topic);

    process.exit(0);
  } catch (error) {
    console.error('Fatal error during analysis agent execution:', error);
    process.exit(1);
  }
}

// Graceful shutdown handlers
process.on('SIGINT', () => {
  console.info('Interrupted, shutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.info('Termination signal received, shutting down...');
  process.exit(0);
});

main();