import { llmClient } from "../llm/llmClient"
import config from "../config"
import humanReviewHook from "../humanReviewHook"
import templates from "./templates.json"

export interface EdgeCaseProbingResult {
  probes: string[]
  confidence: number
}

/**
 * Perform edge case probing on extracted intents to surface potential corner cases.
 * If the LLM confidence is below threshold, delegate to human review.
 * @param requirement original requirement text
 * @param intents array of extracted intents
 */
export async function EdgeCaseProbing(requirement: string, intents: string[]): Promise<EdgeCaseProbingResult> {
  const template = templates.edgeCaseProbing
  const prompt = template
    .replace("{{requirement}}", requirement)
    .replace("{{intents}}", JSON.stringify(intents, null, 2))

  let llmResponse: { text: string; confidence?: number }
  try {
    llmResponse = await llmClient.generate({
      prompt,
      temperature: config.chainTemperature,
      maxTokens: config.maxTokens,
    })
  } catch (err) {
    const humanResult = await humanReviewHook("EdgeCaseProbing", {
      requirement,
      intents,
      error: err instanceof Error ? err.message : String(err),
    })
    return {
      probes: humanResult.probes || [],
      confidence: humanResult.confidence ?? 1,
    }
  }

  let parsed: any
  try {
    parsed = JSON.parse(llmResponse.text)
  } catch (err) {
    throw new Error(`EdgeCaseProbing: failed to parse LLM JSON response: ${err}`)
  }

  const probes = Array.isArray(parsed.probes) ? parsed.probes : []
  const confidence = typeof parsed.confidence === "number" ? parsed.confidence : llmResponse.confidence ?? 0

  if (confidence < config.edgeCaseThreshold) {
    const humanResult = await humanReviewHook("EdgeCaseProbing", {
      requirement,
      intents,
      response: parsed,
      confidence,
    })
    return {
      probes: humanResult.probes || [],
      confidence: humanResult.confidence ?? 1,
    }
  }

  return { probes, confidence }
}