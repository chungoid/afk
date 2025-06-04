import { generateWithBackoff } from "../utils/llmClient"
import logger from "../utils/logger"

export interface DecomposeInput {
  requestId: string
  intent: string
  edgeCases: string[]
  context: string[]
}

export interface Task {
  id: string
  title: string
  description: string
  dependencies?: string[]
  metadata?: Record<string, any>
}

const DEFAULT_TEMPERATURE = 0.7
const DEFAULT_MAX_TOKENS = 1000
const MAX_RETRIES = 3
const INITIAL_BACKOFF_MS = 500

/**
 * Decompose a high-level intent and its edge cases into a list of discrete tasks.
 * Calls the LLM with a structured prompt to return a JSON array of Task objects.
 * @param input DecomposeInput containing requestId, intent, edgeCases, and context passages
 * @returns Promise resolving to an array of Task objects
 */
export async function decompose(input: DecomposeInput): Promise<Task[]> {
  const { requestId, intent, edgeCases, context } = input
  const prompt = buildPrompt(requestId, intent, edgeCases, context)

  logger.info({ requestId }, "Step3: Decomposition prompt sent to LLM")

  let response: string
  try {
    response = await generateWithBackoff(
      {
        prompt,
        temperature: DEFAULT_TEMPERATURE,
        max_tokens: DEFAULT_MAX_TOKENS
      },
      {
        retries: MAX_RETRIES,
        initialBackoffMs: INITIAL_BACKOFF_MS
      }
    )
  } catch (err) {
    logger.error({ requestId, err }, "Step3: LLM call failed after retries")
    throw new Error(`Failed to generate decomposition from LLM: ${err.message}`)
  }

  logger.debug({ requestId, response }, "Step3: Raw decomposition response")

  let tasks: Task[]
  try {
    const parsed = JSON.parse(response)
    if (!Array.isArray(parsed)) {
      throw new Error("LLM response is not a JSON array")
    }
    tasks = parsed.map((t: any) => ({
      id: String(t.id),
      title: String(t.title),
      description: String(t.description),
      dependencies: Array.isArray(t.dependencies) ? t.dependencies.map(String) : [],
      metadata: typeof t.metadata === "object" && t.metadata !== null ? t.metadata : {}
    }))
  } catch (err) {
    logger.error({ requestId, err, response }, "Step3: Failed to parse decomposition JSON")
    throw new Error(`Error parsing tasks from LLM response: ${err.message}`)
  }

  logger.info({ requestId, count: tasks.length }, "Step3: Decomposition produced tasks")
  return tasks
}

/**
 * Builds the prompt for the decomposition step.
 */
function buildPrompt(
  requestId: string,
  intent: string,
  edgeCases: string[],
  context: string[]
): string {
  const edgeList = edgeCases.length
    ? edgeCases.map((e, i) => `${i + 1}. ${e}`).join("\n")
    : "None"
  const contextBlock = context.length
    ? context.map((c, i) => `Context ${i + 1}:\n${c}`).join("\n\n")
    : "No additional context."

  return `
You are an AI assistant specialized in breaking down high-level requirements into actionable tasks.
Request ID: ${requestId}

Primary Intent:
${intent}

Edge Cases and Exceptions:
${edgeList}

Relevant Context Passages:
${contextBlock}

Instructions:
Based on the primary intent and edge cases, decompose the requirement into a list of discrete tasks.
Each task must be a JSON object with the following fields:
- id: a unique string identifier
- title: a short descriptive title
- description: detailed description of the work to be done
- dependencies: an array of ids of tasks that must be done before this one (optional)
- metadata: an object for any additional information (optional)

Return strictly a JSON array of task objects, with no additional text or markdown.
`
}