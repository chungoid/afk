import { init, upsert, query, embed } from '../../src/services/vectorStore'
import { PineconeClient } from '@pinecone-database/pinecone'
import * as llmClient from '../../src/services/llmClient'

jest.mock('@pinecone-database/pinecone')
jest.mock('../../src/services/llmClient')

const mockInit = jest.fn()
const mockUpsert = jest.fn()
const mockQuery = jest.fn()
const mockIndex = jest.fn(() => ({
  upsert: mockUpsert,
  query: mockQuery
}))

;(PineconeClient as jest.Mock).mockImplementation(() => ({
  init: mockInit,
  Index: mockIndex
}))

describe('vectorStore service', () => {
  const apiKey = 'test-api-key'
  const environment = 'test-env'
  const indexName = 'test-index'

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('initializes Pinecone client and selects index', async () => {
    await init(apiKey, environment, indexName)
    expect(PineconeClient).toHaveBeenCalledTimes(1)
    expect(mockInit).toHaveBeenCalledWith({ apiKey, environment })
    expect(mockIndex).toHaveBeenCalledWith(indexName)
  })

  it('upserts a vector with metadata', async () => {
    const id = 'task_123'
    const vector = [0.1, 0.2, 0.3]
    const metadata = { foo: 'bar' }
    await init(apiKey, environment, indexName)
    await upsert(id, vector, metadata)
    expect(mockUpsert).toHaveBeenCalledWith({
      upsertRequest: {
        vectors: [
          {
            id,
            values: vector,
            metadata
          }
        ]
      }
    })
  })

  it('queries the index and returns metadata.text snippets', async () => {
    const vector = [1, 2, 3]
    const topK = 3
    const matches = [
      { id: '1', score: 0.9, metadata: { text: 'snippet1' } },
      { id: '2', score: 0.8, metadata: { text: 'snippet2' } }
    ]
    mockQuery.mockResolvedValue({ matches })
    await init(apiKey, environment, indexName)
    const result = await query(vector, topK)
    expect(mockQuery).toHaveBeenCalledWith({
      queryRequest: {
        vector,
        topK,
        includeMetadata: true
      }
    })
    expect(result).toEqual(['snippet1', 'snippet2'])
  })

  it('embeds text using llmClient.embed', async () => {
    const text = 'hello world'
    const embedding = [0.5, 0.6, 0.7]
    ;(llmClient.embed as jest.Mock).mockResolvedValue(embedding)
    const result = await embed(text)
    expect(llmClient.embed).toHaveBeenCalledWith(text)
    expect(result).toEqual(embedding)
  })

  it('throws if query fails', async () => {
    const vector = [1, 2, 3]
    const topK = 1
    const error = new Error('query failed')
    mockQuery.mockRejectedValue(error)
    await init(apiKey, environment, indexName)
    await expect(query(vector, topK)).rejects.toThrow('query failed')
  })
})