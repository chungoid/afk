import pino from 'pino'
import llmClient from '../../services/llmClient'

const logger = pino({ level: process.env.LOG_LEVEL || 'info' })
const MAX_ITERATIONS = 3

export interface Task {
  id: string
  title: string
  description: string
  dependencies: string[]
  metadata?: Record<string, any>
}

export interface Intent {
  objectives: string[]
  constraints?: string[]
  [key: string]: any
}

/**
 * Decompose a given intent into discrete tasks.
 * Uses a multi-turn LLM prompt chain to enumerate tasks and handle pagination.
 * @param intent Structured intent object from intentExtractor
 * @param context Array of context snippets from RAG retrieval
 * @returns Array of Task objects matching JSON Schema
 */
export async function decompose(intent: Intent, context: string[]): Promise<Task[]> {
  const allTasks: Task[] = []
  let iteration = 0

  try {
    while (iteration < MAX_ITERATIONS) {
      iteration++
      const prompt = buildPrompt(intent, context, allTasks, iteration)
      logger.debug({ iteration, prompt }, 'Decomposer prompt')
      const response = await llmClient.chat([{ role: 'user', content: prompt }])
      const content = response.choices?.[0]?.message?.content
      if (!content) {
        logger.warn({ iteration }, 'Empty LLM response, ending decomposition')
        break
      }
      const newTasks = parseTasksFromContent(content)
      if (newTasks.length === 0) {
        logger.info({ iteration }, 'No additional tasks found, ending decomposition')
        break
      }
      // Deduplicate by id
      for (const t of newTasks) {
        if (!allTasks.find(existing => existing.id === t.id)) {
          allTasks.push(t)
        }
      }
      // If we've reached a stable state, stop
      if (newTasks.length === 0) {
        break
      }
    }
    logger.info({ totalTasks: allTasks.length }, 'Decomposition complete')
    return allTasks
  } catch (error) {
    logger.error({ err: error }, 'Error in decomposer step')
    throw error
  }
}

function buildPrompt(intent: Intent, context: string[], existingTasks: Task[], iteration: number): string {
  if (iteration === 1) {
    return `
You are a software analysis assistant. Decompose the user intent into discrete tasks.
User intent:
${JSON.stringify(intent, null, 2)}

Context snippets:
${context.map((c, i) => `Context ${i + 1}:\n${c}`).join('\n\n')}

Please output a JSON array of tasks. Each task must match this structure:
{
  "id": "task_<lowercase_alphanumeric>",
  "title": "<short title>",
  "description": "<detailed description>",
  "dependencies": [/* list of task IDs this task depends on */],
  "metadata": { /* optional key-value pairs */ }
}
Only return the JSON array. Do not include any extra text.
`
  } else {
    return `
We have already identified the following tasks:
${JSON.stringify(existingTasks, null, 2)}

Based on the original intent:
${JSON.stringify(intent, null, 2)}

Are there any additional tasks required to fully implement the intent that were not listed above?
If yes, list them as a JSON array of tasks with the same structure. If no, respond with an empty JSON array [].
Only return the JSON array.
`
  }
}

function parseTasksFromContent(content: string): Task[] {
  let jsonArray: any
  try {
    jsonArray = JSON.parse(content)
  } catch {
    const start = content.indexOf('[')
    const end = content.lastIndexOf(']')
    if (start >= 0 && end >= 0) {
      try {
        jsonArray = JSON.parse(content.slice(start, end + 1))
      } catch (err) {
        throw new Error(`Failed to parse JSON tasks from content: ${err}`)
      }
    } else {
      throw new Error('Response does not contain a JSON array of tasks')
    }
  }
  if (!Array.isArray(jsonArray)) {
    throw new Error('Parsed result is not an array')
  }
  // Basic shape check
  return jsonArray.map((t: any) => {
    return {
      id: String(t.id),
      title: String(t.title),
      description: String(t.description),
      dependencies: Array.isArray(t.dependencies) ? t.dependencies.map(String) : [],
      metadata: t.metadata && typeof t.metadata === 'object' ? t.metadata : {}
    } as Task
  })
}