import templates from './templates.json'
import { config } from '../config'
import { humanReviewHook } from '../humanReviewHook'
import { llmClient } from '../utils/llmClient'

export interface IntentExtractionResult {
  intents: string[]
  confidence: number
}

export async function intentExtraction(input: string): Promise<IntentExtractionResult> {
  const prompt = templates.intentExtraction.replace('{{input}}', input)
  let response
  try {
    response = await llmClient.generate({ prompt })
  } catch (err) {
    throw new Error(`IntentExtraction LLM call failed: ${(err as Error).message}`)
  }
  let result: IntentExtractionResult
  try {
    const parsed = JSON.parse(response.text)
    if (!Array.isArray(parsed.intents) || typeof parsed.confidence !== 'number') {
      throw new Error('LLM response missing required fields')
    }
    result = { intents: parsed.intents, confidence: parsed.confidence }
  } catch (err) {
    throw new Error(`Failed to parse IntentExtraction response: ${(err as Error).message}`)
  }
  if (result.confidence < config.intentThreshold) {
    try {
      await humanReviewHook({
        step: 'IntentExtraction',
        input,
        output: result
      })
    } catch (hookErr) {
      // log hook error but do not fail pipeline
      console.error('humanReviewHook failed for IntentExtraction:', hookErr)
    }
  }
  return result
}