import { PineconeClient, ScoredVector } from '@pinecone-database/pinecone'
import config from '../config/default'
import logger from '../utils/logger'
import { injectable } from 'tsyringe'

@injectable()
class PineconeClientService {
  private client: PineconeClient
  private indexName: string
  private namespace?: string
  private initialized: boolean = false

  constructor() {
    const { PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX, PINECONE_NAMESPACE } = config
    if (!PINECONE_API_KEY || !PINECONE_ENVIRONMENT || !PINECONE_INDEX) {
      throw new Error('Missing required Pinecone configuration')
    }
    this.client = new PineconeClient()
    this.indexName = PINECONE_INDEX
    this.namespace = PINECONE_NAMESPACE
    this.initialize(PINECONE_API_KEY, PINECONE_ENVIRONMENT).catch(err => {
      logger.error('Pinecone initialization failed', { error: err })
    })
  }

  private async initialize(apiKey: string, environment: string): Promise<void> {
    await this.client.init({ apiKey, environment })
    this.initialized = true
    logger.info('Pinecone client initialized', { index: this.indexName, namespace: this.namespace })
  }

  async upsert(vectors: Array<{ id: string; values: number[]; metadata?: Record<string, any> }>): Promise<void> {
    if (!this.initialized) {
      throw new Error('Pinecone client not initialized')
    }
    try {
      await this.client.Index(this.indexName).upsert({
        upsertRequest: {
          vectors,
          namespace: this.namespace
        }
      })
      logger.info('Upserted vectors to Pinecone', { count: vectors.length })
    } catch (error) {
      logger.error('Error upserting vectors to Pinecone', { error })
      throw error
    }
  }

  async query(vector: number[], topK: number = 5): Promise<ScoredVector[]> {
    if (!this.initialized) {
      throw new Error('Pinecone client not initialized')
    }
    try {
      const response = await this.client.Index(this.indexName).query({
        queryRequest: {
          vector,
          topK,
          includeMetadata: true,
          namespace: this.namespace
        }
      })
      logger.info('Queried Pinecone for similar vectors', { topK, matches: response.matches?.length })
      return response.matches ?? []
    } catch (error) {
      logger.error('Error querying Pinecone', { error })
      throw error
    }
  }
}

export default new PineconeClientService()