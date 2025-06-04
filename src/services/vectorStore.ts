import { PineconeClient } from '@pinecone-database/pinecone'
import OpenAI from 'openai'
import config from 'config'
import pino from 'pino'

const logger = pino({ name: 'vectorStore' })

class VectorStore {
  private static pinecone: PineconeClient
  private static openai: OpenAI
  private static indexName: string

  /**
   * Initialize Pinecone and OpenAI clients using configuration or environment variables.
   */
  static async init(): Promise<void> {
    try {
      const pineconeApiKey = process.env.PINECONE_API_KEY || config.get<string>('pinecone.apiKey')
      const pineconeEnv = process.env.PINECONE_ENVIRONMENT || config.get<string>('pinecone.environment')
      VectorStore.indexName = config.get<string>('pinecone.indexName')
      VectorStore.pinecone = new PineconeClient()
      await VectorStore.pinecone.init({ apiKey: pineconeApiKey, environment: pineconeEnv })
      const openaiApiKey = process.env.OPENAI_API_KEY || config.get<string>('openai.apiKey')
      VectorStore.openai = new OpenAI({ apiKey: openaiApiKey })
      logger.info('VectorStore initialized successfully')
    } catch (err) {
      logger.error({ err }, 'Failed to initialize VectorStore')
      throw err
    }
  }

  /**
   * Generate an embedding vector for the given text using OpenAI Embeddings API.
   * @param text - Input text to embed
   * @returns embedding vector as an array of floats
   */
  static async embed(text: string): Promise<number[]> {
    try {
      const model = config.get<string>('openai.embeddingModel')
      const response = await VectorStore.openai.embeddings.create({ model, input: text })
      if (!response.data.length) {
        throw new Error('No embedding returned from OpenAI')
      }
      return response.data[0].embedding
    } catch (err) {
      logger.error({ err, text }, 'Error generating embedding')
      throw err
    }
  }

  /**
   * Upsert a vector with metadata into the Pinecone index.
   * @param id - Unique identifier for the vector
   * @param vector - Embedding vector
   * @param metadata - Associated metadata object
   */
  static async upsert(id: string, vector: number[], metadata: Record<string, any>): Promise<void> {
    try {
      const index = VectorStore.pinecone.Index(VectorStore.indexName)
      await index.upsert({
        upsertRequest: {
          vectors: [{ id, values: vector, metadata }]
        }
      })
      logger.info({ id }, 'Upserted vector successfully')
    } catch (err) {
      logger.error({ err, id }, 'Error upserting vector')
      throw err
    }
  }

  /**
   * Query the Pinecone index for nearest neighbor vectors and return context snippets.
   * @param vector - Query embedding vector
   * @param topK - Number of top results to retrieve
   * @returns Array of context snippets extracted from metadata
   */
  static async query(vector: number[], topK = 5): Promise<string[]> {
    try {
      const index = VectorStore.pinecone.Index(VectorStore.indexName)
      const result = await index.query({
        queryRequest: {
          vector,
          topK,
          includeMetadata: true,
          includeValues: false
        }
      })
      const snippets = result.matches
        .map(m => (m.metadata as any)?.text as string)
        .filter(Boolean)
      logger.info({ topK, retrieved: snippets.length }, 'Query completed')
      return snippets
    } catch (err) {
      logger.error({ err }, 'Error querying vectors')
      throw err
    }
  }
}

export default VectorStore