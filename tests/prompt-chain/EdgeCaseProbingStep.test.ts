import EdgeCaseProbingStep from '../../../src/prompt-chain/steps/EdgeCaseProbingStep'
import { PromptContext } from '../../../src/prompt-chain/PromptChain'

describe('EdgeCaseProbingStep', () => {
  let mockLLM: { generate: jest.Mock }
  let step: EdgeCaseProbingStep
  const baseContext: PromptContext = {
    requirementText: 'A requirement to validate',
    memory: [],
    generatedTasks: []
  }

  beforeEach(() => {
    mockLLM = { generate: jest.fn() }
    step = new EdgeCaseProbingStep(mockLLM)
  })

  it('should call LLM with correct prompt and store parsed edge cases', async () => {
    const mockResponse = '["Edge1","Edge2"]'
    mockLLM.generate.mockResolvedValueOnce(mockResponse)
    const result = await step.execute({ ...baseContext, memory: [] })
    expect(mockLLM.generate).toHaveBeenCalledWith(
      expect.objectContaining({
        prompt: expect.stringContaining('A requirement to validate')
      })
    )
    expect(result.edgeCases).toEqual(['Edge1', 'Edge2'])
    expect(result.memory).toEqual([
      { role: 'user', content: expect.stringContaining('Identify edge cases') },
      { role: 'assistant', content: mockResponse }
    ])
  })

  it('should handle empty edge case list', async () => {
    const mockResponse = '[]'
    mockLLM.generate.mockResolvedValueOnce(mockResponse)
    const result = await step.execute({ ...baseContext, memory: [] })
    expect(result.edgeCases).toEqual([])
    expect(result.memory).toContainEqual({ role: 'assistant', content: mockResponse })
  })

  it('should throw an error when LLM returns invalid JSON', async () => {
    mockLLM.generate.mockResolvedValueOnce('invalid json')
    await expect(step.execute({ ...baseContext, memory: [] })).rejects.toThrow('Failed to parse edge cases JSON')
  })
})