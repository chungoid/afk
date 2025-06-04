import { randomBytes } from "crypto"

export interface VectorStoreItem {
  id: string
  vector: number[]
  metadata: any
}

export interface QueryResult {
  id: string
  metadata: any
  score: number
}

/**
 * A simple in-memory vector store adapter stub.
 * Supports embed, upsert, and query operations.
 */
export class VectorStoreAdapter {
  private store: VectorStoreItem[] = []
  private readonly dimension: number
  private readonly defaultTopK: number

  /**
   * @param dimension dimensionality of the embedding vectors
   * @param defaultTopK default number of results to return on query
   */
  constructor(dimension = 768, defaultTopK = 5) {
    this.dimension = dimension
    this.defaultTopK = defaultTopK
  }

  /**
   * Generates a deterministic pseudo-embedding for the given text.
   * @param text input text to embed
   * @returns embedding vector of length `dimension`
   */
  async embed(text: string): Promise<number[]> {
    // Create a hash from the text to seed the PRNG
    const seed = randomBytes(4).readUInt32BE(0) ^ text.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0)
    const vector: number[] = []
    let value = seed
    for (let i = 0; i < this.dimension; i++) {
      // Linear congruential generator for repeatable pseudo-random numbers
      value = (value * 1664525 + 1013904223) & 0xffffffff
      vector.push((value >>> 0) / 0xffffffff)
    }
    return vector
  }

  /**
   * Upserts multiple items into the in-memory store.
   * @param items array of items with id, vector, and metadata
   */
  async upsert(items: VectorStoreItem[]): Promise<void> {
    for (const item of items) {
      const idx = this.store.findIndex(s => s.id === item.id)
      if (idx !== -1) {
        this.store[idx] = item
      } else {
        this.store.push(item)
      }
    }
  }

  /**
   * Queries the store for the topK most similar items to the provided vector.
   * @param queryVector the embedding vector to query against
   * @param topK number of top results to return
   * @returns array of QueryResult sorted by descending score
   */
  async query(queryVector: number[], topK = this.defaultTopK): Promise<QueryResult[]> {
    if (queryVector.length !== this.dimension) {
      throw new Error(`Query vector dimension ${queryVector.length} does not match store dimension ${this.dimension}`)
    }
    const scored = this.store.map(item => ({
      id: item.id,
      metadata: item.metadata,
      score: this.cosineSimilarity(queryVector, item.vector)
    }))
    scored.sort((a, b) => b.score - a.score)
    return scored.slice(0, topK)
  }

  /**
   * Computes cosine similarity between two vectors.
   * @param a first vector
   * @param b second vector
   * @returns cosine similarity in [-1,1]
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    let dot = 0
    let normA = 0
    let normB = 0
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i]
      normA += a[i] * a[i]
      normB += b[i] * b[i]
    }
    if (normA === 0 || normB === 0) {
      return 0
    }
    return dot / (Math.sqrt(normA) * Math.sqrt(normB))
  }
}

export const vectorStoreAdapter = new VectorStoreAdapter()