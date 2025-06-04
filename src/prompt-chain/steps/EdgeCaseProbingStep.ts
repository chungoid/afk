import { PromptStep, PromptContext } from '../PromptChain'
import { ILLMClient, ChatMessage } from '../llm/LLMClient'

export class EdgeCaseProbingStep extends PromptStep {
  constructor(private llmClient: ILLMClient) {
    super()
  }

  async execute(ctx: PromptContext): Promise<PromptContext> {
    const systemPrompt: ChatMessage = {
      role: 'system',
      content: 'You are an expert software engineer specialized in identifying potential edge cases from requirements.'
    }
    const userPrompt: ChatMessage = {
      role: 'user',
      content: `Here is the requirement:\n${ctx.requirementText}\n\nList all potential edge cases or corner scenarios for this requirement as a JSON array of strings.`
    }
    const messages: ChatMessage[] = [...ctx.memory, systemPrompt, userPrompt]
    let assistantContent: string
    try {
      const response = await this.llmClient.chat(messages)
      if (!response.choices || response.choices.length === 0 || !response.choices[0].message) {
        throw new Error('No valid response from LLM')
      }
      assistantContent = response.choices[0].message.content.trim()
    } catch (err: any) {
      throw new Error(`EdgeCaseProbingStep LLM error: ${err.message}`)
    }

    let edgeCases: string[]
    try {
      const parsed = JSON.parse(assistantContent)
      if (!Array.isArray(parsed) || !parsed.every(item => typeof item === 'string')) {
        throw new Error('Response JSON is not an array of strings')
      }
      edgeCases = parsed
    } catch (err: any) {
      throw new Error(`EdgeCaseProbingStep parse error: ${err.message}. Response: ${assistantContent}`)
    }

    const newMemory = messages.concat({ role: 'assistant', content: assistantContent })
    return {
      ...ctx,
      memory: newMemory,
      edgeCases
    }
  }
}