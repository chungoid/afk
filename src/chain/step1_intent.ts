import { injectable, inject } from 'tsyringe'
import { backOff } from 'exponential-backoff'
import { LLMClient } from '../app/llmClient'
import { logger } from '../utils/logger'
import { metrics } from '../utils/metrics'

export interface ExtractIntentOptions {
  requestId: string
  requirement: string
  contextPassages?: string[]
}

export interface IntentExtractionResult {
  intent: string
}

@injectable()
export class IntentExtractor {
  private readonly maxRetries = 3

  constructor(@inject('LLMClient') private llmClient: LLMClient) {}

  public async extract(options: ExtractIntentOptions): Promise<IntentExtractionResult> {
    const { requestId, requirement, contextPassages } = options
    const prompt = this.buildPrompt(requirement, contextPassages)
    let responseText = ''
    const start = Date.now()
    try {
      const response = await backOff(
        () => this.llmClient.call({ prompt, temperature: 0, maxTokens: 200 }),
        {
          startingDelay: 500,
          maxRetries: this.maxRetries,
          retry: err => {
            logger.warn(`[IntentExtractor][${requestId}] retrying due to error: ${err.message}`)
            return true
          },
        }
      )
      responseText = response.text
      const durationMs = Date.now() - start
      metrics.histogram('chain_step1_intent_latency_ms', durationMs, { step: 'intent_extraction' })
      const intent = this.parseResponse(responseText)
      return { intent }
    } catch (err: any) {
      const durationMs = Date.now() - start
      metrics.histogram('chain_step1_intent_failure_latency_ms', durationMs, { step: 'intent_extraction' })
      logger.error(
        `[IntentExtractor][${requestId}] failed to extract intent: ${err.message}`,
        { error: err, prompt, responseText }
      )
      throw err
    }
  }

  private buildPrompt(requirement: string, contextPassages?: string[]): string {
    const contextSection =
      contextPassages && contextPassages.length > 0
        ? `Here are related past decisions to consider:\n${contextPassages
            .map((p, i) => `${i + 1}. ${p}`)
            .join('\n')}\n\n`
        : ''
    return (
      contextSection +
      `Requirement:\n${requirement}\n\n` +
      `Extract the primary intent of this requirement in a concise phrase. ` +
      `Respond ONLY with a JSON object in the following format:\n` +
      `{"intent":"<IntentPhrase>"}\n`
    )
  }

  private parseResponse(text: string): string {
    try {
      const idx = text.indexOf('{')
      if (idx < 0) throw new Error('No JSON object found in response')
      const jsonText = text.substring(idx)
      const parsed = JSON.parse(jsonText)
      if (!parsed.intent || typeof parsed.intent !== 'string') {
        throw new Error('Parsed JSON does not contain a string "intent" field')
      }
      return parsed.intent.trim()
    } catch (err: any) {
      throw new Error(
        `Unable to parse intent extraction response: ${err.message}. Raw response: ${text}`
      )
    }
  }
}