import { llmClient } from '../../services/llmClient'
import config from 'config'

export interface IntentExtractionResult {
  intent: string
  objectives: string[]
  constraints: string[]
}

/**
 * Extracts user intent, objectives, and constraints from a raw requirement string.
 * Sends a structured prompt to the LLM and parses the JSON response.
 * @param requirement - The raw requirement text to analyze.
 * @returns A promise resolving to the extracted intent object.
 * @throws Error if the LLM call fails or the response cannot be parsed/validated.
 */
export async function extractIntent(requirement: string): Promise<IntentExtractionResult> {
  const llmParams = config.get<Record<string, any>>('llm.intentExtractor')
  const systemPrompt = 'You are an AI assistant that analyzes user requirements.'
  const userPrompt = `
Extract the user's intent, objectives, and constraints from the following requirement.  
Respond ONLY with a JSON object with the keys "intent" (string), "objectives" (array of strings), and "constraints" (array of strings).

Requirement:
"""${requirement}"""
`

  try {
    const response = await llmClient.chatCompletion({
      model: llmParams.model,
      temperature: llmParams.temperature,
      max_tokens: llmParams.maxTokens,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt.trim() }
      ]
    })

    const message = response.choices?.[0]?.message?.content
    if (!message) {
      throw new Error('Empty response from LLM for intent extraction')
    }

    let parsed: any
    try {
      parsed = JSON.parse(message)
    } catch (err) {
      throw new Error(`Failed to parse JSON from LLM response: ${(err as Error).message}`)
    }

    if (
      typeof parsed.intent !== 'string' ||
      !Array.isArray(parsed.objectives) ||
      !Array.isArray(parsed.constraints) ||
      !parsed.objectives.every(o => typeof o === 'string') ||
      !parsed.constraints.every(c => typeof c === 'string')
    ) {
      throw new Error(`Invalid intent extraction schema: ${JSON.stringify(parsed)}`)
    }

    return {
      intent: parsed.intent,
      objectives: parsed.objectives,
      constraints: parsed.constraints
    }
  } catch (error) {
    const err = error as Error
    console.error('Error in extractIntent:', err.message)
    throw err
  }
}