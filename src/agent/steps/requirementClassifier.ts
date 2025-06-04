import { llmClient } from '../../services/llmClient'

export type RequirementType = 'typical' | 'edge'

export interface RequirementClassification {
  classification: RequirementType
  reasoning: string
}

/**
 * Classify a raw requirement string as either a typical requirement or an edge-case requirement.
 * Uses the LLM client to perform the classification and returns a structured result.
 *
 * @param requirement - The raw requirement text to classify
 * @returns An object containing the classification and the LLM’s reasoning
 * @throws Error if the LLM call fails or returns invalid JSON
 */
export async function classifyRequirement(requirement: string): Promise<RequirementClassification> {
  const systemPrompt = 'You are an intelligent software analyst. Classify the following requirement as either a typical requirement or an edge-case requirement. Respond only in valid JSON with two keys: "classification" (with value "typical" or "edge") and "reasoning" (a brief explanation).'
  const userPrompt = `Requirement: """${requirement}"""`

  try {
    const response = await llmClient.chat([
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ])

    const text = response.choices?.[0]?.message?.content?.trim()
    if (!text) {
      throw new Error('Empty response from LLM during requirement classification')
    }

    let parsed: any
    try {
      parsed = JSON.parse(text)
    } catch (err) {
      throw new Error(`Failed to parse LLM response as JSON: ${text}`)
    }

    const { classification, reasoning } = parsed
    if (
      (classification !== 'typical' && classification !== 'edge') ||
      typeof reasoning !== 'string'
    ) {
      throw new Error(`Invalid classification output: ${text}`)
    }

    return { classification, reasoning }
  } catch (err: any) {
    // Re-throw with context for upstream error handling/logging
    throw new Error(`requirementClassifier failed: ${err.message || err}`)
  }
}