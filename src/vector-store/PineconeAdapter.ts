import { PineconeClient } from '@pinecone-database/pinecone'
import { OpenAI } from 'openai'
import { IVectorStoreAdapter, ContextFragment } from './IVectorStoreAdapter'

export class PineconeAdapter implements IVectorStoreAdapter {
  private pineconeClient: PineconeClient
  private indexName: string
  private index: any
  private openai: OpenAI
  private model: string
  private initialized = false

  /**
   * Constructs a new PineconeAdapter.
   * @param pineconeApiKey - API key for Pinecone
   * @param pineconeEnvironment - Environment/region for Pinecone
   * @param indexName - Name of the Pinecone index to use
   * @param openaiApiKey - API key for OpenAI embeddings
   * @param openaiModel - OpenAI embedding model (defaults to text-embedding-ada-002)
   */
  constructor(
    pineconeApiKey: string,
    pineconeEnvironment: string,
    indexName: string,
    openaiApiKey: string,
    openaiModel = 'text-embedding-ada-002'
  ) {
    if (!pineconeApiKey || !pineconeEnvironment || !indexName || !openaiApiKey) {
      throw new Error('PineconeAdapter requires pineconeApiKey, pineconeEnvironment, indexName, and openaiApiKey')
    }
    this.pineconeClient = new PineconeClient()
    this.indexName = indexName
    this.openai = new OpenAI({ apiKey: openaiApiKey })
    this.model = openaiModel

    // Initialize Pinecone client
    this.pineconeClient
      .init({ apiKey: pineconeApiKey, environment: pineconeEnvironment })
      .catch(err => {
        console.error('Failed to initialize Pinecone client', err)
      })
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      this.index = this.pineconeClient.Index(this.indexName)
      this.initialized = true
    }
  }

  /**
   * Generate an embedding for the given text using OpenAI.
   * @param text - The text to embed
   * @returns A numeric vector embedding
   */
  async embed(text: string): Promise<number[]> {
    try {
      const response = await this.openai.embeddings.create({
        model: this.model,
        input: text
      })
      if (!response.data || response.data.length === 0) {
        throw new Error('No embedding returned from OpenAI')
      }
      return response.data[0].embedding
    } catch (err: any) {
      throw new Error(`PineconeAdapter.embed error: ${err.message || err}`)
    }
  }

  /**
   * Upsert a vector into Pinecone index.
   * @param id - Unique identifier for the vector
   * @param vector - The numeric vector to upsert
   * @param metadata - Associated metadata object
   */
  async upsert(id: string, vector: number[], metadata: any): Promise<void> {
    try {
      await this.ensureInitialized()
      await this.index.upsert({
        vectors: [
          {
            id,
            values: vector,
            metadata
          }
        ]
      })
    } catch (err: any) {
      throw new Error(`PineconeAdapter.upsert error for id ${id}: ${err.message || err}`)
    }
  }

  /**
   * Query the Pinecone index for nearest neighbors.
   * @param vector - The query vector
   * @param topK - Number of nearest results to return
   * @returns Array of ContextFragments with id, score, and metadata
   */
  async query(vector: number[], topK: number): Promise<ContextFragment[]> {
    try {
      await this.ensureInitialized()
      const response = await this.index.query({
        vector,
        topK,
        includeMetadata: true
      })
      const matches = response.matches ?? []
      return matches.map((match: any) => ({
        id: match.id,
        score: match.score ?? 0,
        metadata: match.metadata ?? {}
      }))
    } catch (err: any) {
      throw new Error(`PineconeAdapter.query error: ${err.message || err}`)
    }
  }
}