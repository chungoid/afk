/**
 * A fragment of contextual data returned from the vector store.
 */
export interface ContextFragment {
  /** Unique identifier of the stored item */
  id: string
  /** The original text content associated with the vector */
  text: string
  /** Optional arbitrary metadata stored alongside the vector */
  metadata?: Record<string, any>
  /** Similarity or relevance score from the query */
  score: number
}

/**
 * Adapter interface for pluggable vector store implementations.
 */
export interface IVectorStoreAdapter {
  /**
   * Generate an embedding vector for the given text.
   * @param text - The input text to embed.
   * @returns A promise resolving to an array of numbers representing the embedding.
   */
  embed(text: string): Promise<number[]>

  /**
   * Upsert a vector into the store with associated metadata.
   * @param id - Unique identifier for the vector entry.
   * @param vector - The numerical embedding vector.
   * @param metadata - Arbitrary data to associate with this vector.
   */
  upsert(id: string, vector: number[], metadata: Record<string, any>): Promise<void>

  /**
   * Query the store for top-K most similar vectors to the provided one.
   * @param vector - The embedding vector to query against.
   * @param topK - Number of top results to return.
   * @returns A promise resolving to an array of context fragments.
   */
  query(vector: number[], topK: number): Promise<ContextFragment[]>
}