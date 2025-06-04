import { OpenAIApi, Configuration } from 'openai'
import pineconeClient from './pineconeClient'
import config from '../config/default'
import logger from '../utils/logger'

export interface ContextDocument {
  id: string
  score: number
  metadata: Record<string, any>
}

/**
 * VectorRetriever is responsible for encoding input text into embeddings
 * and querying the Pinecone vector store for nearest neighbor documents.
 */
export class VectorRetriever {
  private openAI: OpenAIApi
  private index: any

  constructor() {
    const openAIConfig = new Configuration({
      apiKey: config.openai.apiKey
    })
    this.openAI = new OpenAIApi(openAIConfig)
    this.index = pineconeClient.Index(config.pinecone.indexName)
  }

  /**
   * fetchRelated takes a text query, encodes it, and returns the top K
   * matching context documents from Pinecone.
   * @param query - the raw text to retrieve context for
   * @param topK - number of results to return (default 5)
   */
  async fetchRelated(query: string, topK = 5): Promise<ContextDocument[]> {
    try {
      logger.info({ query, topK }, 'VectorRetriever: encoding query')
      const embedRes = await this.openAI.createEmbedding({
        model: config.embedding.model,
        input: query
      })
      const vector = embedRes.data.data[0].embedding
      logger.debug({ length: vector.length }, 'VectorRetriever: embedding generated')

      const queryRequest: Record<string, any> = {
        vector,
        topK,
        includeMetadata: true
      }
      if (config.pinecone.namespace) {
        queryRequest.namespace = config.pinecone.namespace
      }

      logger.info({ topK }, 'VectorRetriever: querying Pinecone')
      const response = await this.index.query({ queryRequest })

      const matches = response.matches ?? []
      const results = matches.map(m => ({
        id: m.id,
        score: m.score,
        metadata: m.metadata ?? {}
      }))

      logger.info({ count: results.length }, 'VectorRetriever: retrieval complete')
      return results
    } catch (err: any) {
      logger.error({ err }, 'VectorRetriever: failed to fetch related documents')
      throw new Error(`VectorRetrieverError: ${err.message}`)
    }
  }
}

export default new VectorRetriever()