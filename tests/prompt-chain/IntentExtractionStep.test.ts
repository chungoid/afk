import IntentExtractionStep from '../../src/prompt-chain/steps/IntentExtractionStep'
import { PromptContext } from '../../src/prompt-chain/PromptChain'
import { ValidationError } from '../../src/validation/ValidationError'

describe('IntentExtractionStep', () => {
  let mockLlmClient: { call: jest.Mock }
  let mockValidator: { validate: jest.Mock }
  let step: IntentExtractionStep
  let baseContext: PromptContext

  beforeEach(() => {
    mockLlmClient = { call: jest.fn() }
    mockValidator = { validate: jest.fn() }
    step = new IntentExtractionStep(mockLlmClient, mockValidator)
    baseContext = { requirementText: 'Some requirement text', memory: [] }
  })

  it('parses valid JSON response and returns generatedTasks', async () => {
    const tasks = [
      { id: '1', description: 'Test task', metadata: { priority: 1, sourceRequirementId: 'req-1' } }
    ]
    const llmResponse = { text: JSON.stringify({ tasks }) }
    mockLlmClient.call.mockResolvedValue(llmResponse)
    mockValidator.validate.mockReturnValue(tasks)

    const result = await step.execute(baseContext)

    expect(mockLlmClient.call).toHaveBeenCalledWith(expect.stringContaining('Extract tasks'))
    expect(mockValidator.validate).toHaveBeenCalledWith({ tasks })
    expect(result.generatedTasks).toEqual(tasks)
  })

  it('throws SyntaxError on invalid JSON from LLM', async () => {
    mockLlmClient.call.mockResolvedValue({ text: 'not a json' })

    await expect(step.execute(baseContext)).rejects.toThrow(SyntaxError)
  })

  it('throws ValidationError when validator rejects payload', async () => {
    const invalidPayload = { tasks: [{ foo: 'bar' }] }
    mockLlmClient.call.mockResolvedValue({ text: JSON.stringify(invalidPayload) })
    mockValidator.validate.mockImplementation(() => {
      throw new ValidationError('Invalid tasks payload')
    })

    await expect(step.execute(baseContext)).rejects.toThrow(ValidationError)
  })
})