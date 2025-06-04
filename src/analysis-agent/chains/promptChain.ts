import { TaskObject } from '../validation/types'
import config from '../config'
import humanReviewHook from '../humanReviewHook'
import templates from './templates.json'

export interface IntentExtractionResult {
  intents: string[]
  confidence: number
}

export interface EdgeCaseProbingResult {
  probes: string[]
  confidence: number
}

export class PromptChain {
  constructor(private llmClient: { call(prompt: string): Promise<string> }) {}

  async intentExtraction(text: string): Promise<IntentExtractionResult> {
    const prompt = templates.intentExtraction.replace('{{text}}', text)
    let parsed
    try {
      const response = await this.llmClient.call(prompt)
      parsed = JSON.parse(response)
    } catch (err: any) {
      throw new Error(`IntentExtraction failed: ${err.message}`)
    }
    const { intents, confidence } = parsed
    if (confidence < config.intentThreshold) {
      await humanReviewHook('intentExtraction', { text, result: parsed })
    }
    return { intents, confidence }
  }

  async edgeCaseProbing(text: string, intents: string[]): Promise<EdgeCaseProbingResult> {
    const prompt = templates.edgeCaseProbing
      .replace('{{text}}', text)
      .replace('{{intents}}', JSON.stringify(intents))
    let parsed
    try {
      const response = await this.llmClient.call(prompt)
      parsed = JSON.parse(response)
    } catch (err: any) {
      throw new Error(`EdgeCaseProbing failed: ${err.message}`)
    }
    const { probes, confidence } = parsed
    if (confidence < config.edgeCaseThreshold) {
      await humanReviewHook('edgeCaseProbing', { text, intents, result: parsed })
    }
    return { probes, confidence }
  }

  async taskSegmentation(intents: string[], probes: string[]): Promise<TaskObject[]> {
    const prompt = templates.taskSegmentation
      .replace('{{intents}}', JSON.stringify(intents))
      .replace('{{probes}}', JSON.stringify(probes))
    try {
      const response = await this.llmClient.call(prompt)
      const tasks = JSON.parse(response) as TaskObject[]
      return tasks
    } catch (err: any) {
      throw new Error(`TaskSegmentation failed: ${err.message}`)
    }
  }

  async run(rawText: string): Promise<TaskObject[]> {
    const { intents } = await this.intentExtraction(rawText)
    const { probes } = await this.edgeCaseProbing(rawText, intents)
    const tasks = await this.taskSegmentation(intents, probes)
    return tasks
  }
}

export default PromptChain  