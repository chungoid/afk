import * as llmClient from '../../src/services/llmClient'
import { extractIntent } from '../../src/agent/steps/intentExtractor'

jest.mock('../../src/services/llmClient')

interface MockIntent {
  intent: string
  objectives: string[]
  constraints: string[]
}

describe('intentExtractor', () => {
  const mockIntent: MockIntent = {
    intent: 'Book a flight',
    objectives: ['Find cheapest ticket', 'Depart on Friday'],
    constraints: ['No overnight flights', 'Budget < $500']
  }

  beforeEach(() => {
    jest.resetAllMocks()
    ;(llmClient.generate as jest.Mock).mockResolvedValue({ text: JSON.stringify(mockIntent) })
  })

  it('should call LLM client with a prompt containing the requirement and return structured intent', async () => {
    const requirement = 'I need to fly to NYC next Friday with a budget of $500 max, preferably daytime, no overnight layovers.'
    const result = await extractIntent(requirement)

    expect(llmClient.generate).toHaveBeenCalledTimes(1)
    const callArg = (llmClient.generate as jest.Mock).mock.calls[0][0]
    expect(callArg).toHaveProperty('prompt')
    expect(callArg.prompt).toContain(requirement)

    expect(result).toEqual(mockIntent)
  })

  it('should throw SyntaxError when LLM returns invalid JSON', async () => {
    ;(llmClient.generate as jest.Mock).mockResolvedValue({ text: 'not a json' })
    await expect(extractIntent('some requirement')).rejects.toThrow(SyntaxError)
  })

  it('should propagate errors from the LLM client', async () => {
    const llmError = new Error('LLM service unavailable')
    ;(llmClient.generate as jest.Mock).mockRejectedValue(llmError)
    await expect(extractIntent('any requirement')).rejects.toThrow('LLM service unavailable')
  })
})