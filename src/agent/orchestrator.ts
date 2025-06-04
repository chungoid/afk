import config from 'config'
import IntentExtractor from './steps/intentExtractor'
import Decomposer from './steps/decomposer'
import { VectorStore } from '../services/vectorStore'
import { SchemaValidator } from '../services/schemaValidator'
import { Publisher } from '../services/publisher'
import logger from '../services/logger'

export class Orchestrator {
  private intentExtractor: IntentExtractor
  private decomposer: Decomposer
  private vectorStore: VectorStore
  private schemaValidator: SchemaValidator
  private publisher: Publisher

  constructor() {
    const llmConfig = config.get('llm')
    const pineconeConfig = config.get('pinecone')
    const mcpConfig = config.get('mcp')
    const schemaConfig = config.get('schema')
    this.intentExtractor = new IntentExtractor(llmConfig)
    this.decomposer = new Decomposer(llmConfig)
    this.vectorStore = new VectorStore(pineconeConfig)
    this.schemaValidator = new SchemaValidator(schemaConfig)
    this.publisher = new Publisher(mcpConfig)
  }

  async orchestrate(requirement: string): Promise<void> {
    logger.info({ requirement }, 'Orchestration started')
    try {
      const intent = await this.intentExtractor.extractIntent(requirement)
      logger.info({ intent }, 'Intent extracted')

      const embedding = await this.vectorStore.embed(requirement)
      const topK = config.get<number>('rag.topK')
      const contextSnippets = await this.vectorStore.query(embedding, topK)
      logger.info({ count: contextSnippets.length }, 'RAG context retrieved')

      const tasks = await this.decomposer.decompose(intent, contextSnippets)
      logger.info({ count: tasks.length }, 'Tasks decomposed')

      for (const task of tasks) {
        const { valid, errors } = this.schemaValidator.validate(task)
        if (!valid) {
          logger.error({ task, errors }, 'Task schema validation failed')
          throw new Error(`Schema validation failed: ${JSON.stringify(errors)}`)
        }
      }

      const topic = config.get<string>('topics.tasksAnalysis')
      await this.publisher.publish(topic, tasks)
      logger.info({ count: tasks.length, topic }, 'Tasks published successfully')
    } catch (error) {
      logger.error({ err: error }, 'Orchestration error')
      throw error
    }
  }
}

export default new Orchestrator()