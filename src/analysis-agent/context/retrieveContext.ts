import config from '../config'
import VectorStoreAdapter from './vectorStoreAdapter'

const vectorStore = new VectorStoreAdapter()

export async function retrieveContext(reqText: string): Promise<string[]> {
  try {
    const embedding = await vectorStore.embed(reqText)
    const topK = config.vectorStore.topK
    const results = await vectorStore.query(embedding, topK)
    const snippets = results.map(r => r.snippet)
    return snippets
  } catch (err) {
    console.error('retrieveContext error:', err)
    return []
  }
}