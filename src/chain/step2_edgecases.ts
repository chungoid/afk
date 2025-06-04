import { injectable, inject } from 'tsyringe'
import retry from 'async-retry'
import config from '../config/default'
import { LLMClient } from '../utils/llmClient'
import { Logger } from '../utils/logger'

export interface EdgeCase {
  title: string
  description: string
}

@injectable()
export class Step2EdgeCases {
  private readonly promptTemplate: string = `
Given the primary intent below, identify all potential edge cases and exceptions that should be considered. 
List each as a bullet point with a short title and a brief description.

Primary Intent:
"{intent}"
`

  constructor(
    @inject('LLMClient') private llmClient: LLMClient,
    @inject('Logger') private logger: Logger
  ) {}

  /**
   * Generate edge cases for a given intent using the LLM.
   * Retries on transient errors with exponential backoff.
   * @param intent primary intent extracted from the requirement
   * @param requestId correlation id for tracing
   */
  async generateEdgeCases(intent: string, requestId: string): Promise<EdgeCase[]> {
    this.logger.info({ requestId, step: 'Step2EdgeCases', message: 'Generating edge cases' })
    const prompt = this.promptTemplate.replace('{intent}', intent)

    try {
      const response = await retry(
        async (bail, attempt) => {
          this.logger.debug({ requestId, step: 'Step2EdgeCases', attempt, message: 'Calling LLM' })
          const completion = await this.llmClient.chatCompletion({
            model: config.llm.model,
            temperature: config.llm.temperature,
            messages: [{ role: 'system', content: prompt }]
          })
          if (!completion || !completion.choices?.length) {
            throw new Error('Empty response from LLM')
          }
          return completion.choices[0].message?.content ?? ''
        },
        {
          retries: config.llm.maxRetries,
          factor: 2,
          minTimeout: 500,
          onRetry: (err, attempt) => {
            this.logger.warn({ requestId, step: 'Step2EdgeCases', attempt, err, message: 'Retrying LLM call' })
          }
        }
      )

      return this.parseEdgeCases(response)
    } catch (error) {
      this.logger.error({ requestId, step: 'Step2EdgeCases', err: error, message: 'Failed to generate edge cases' })
      throw error
    }
  }

  /**
   * Parse LLM output into structured edge cases.
   */
  private parseEdgeCases(raw: string): EdgeCase[] {
    const lines = raw.split(/\r?\n/).map(line => line.trim()).filter(line => line.startsWith('-'))
    const cases: EdgeCase[] = lines.map(line => {
      const content = line.replace(/^-+\s*/, '')
      const [titlePart, ...descParts] = content.split(/:|\u2013|—/)
      return {
        title: titlePart.trim(),
        description: descParts.join(':').trim()
      }
    })
    return cases
  }
}