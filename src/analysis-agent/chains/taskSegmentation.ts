import config from '../config'
import humanReviewHook from '../humanReviewHook'
import templates from './templates.json'
import { TaskObject } from '../validation/types'
import { llmClient } from '../clients/llmClient'

export async function TaskSegmentation(intents: unknown, probes: unknown): Promise<TaskObject[]> {
  const rawPrompt = templates.taskSegmentation
    .replace('{{intents}}', JSON.stringify(intents))
    .replace('{{probes}}', JSON.stringify(probes))
  let llmResponse
  try {
    llmResponse = await llmClient.generate({ prompt: rawPrompt })
  } catch (err) {
    throw new Error(`LLM call failed in TaskSegmentation: ${err}`)
  }
  const { text, confidence } = llmResponse
  let tasks: TaskObject[]
  try {
    tasks = JSON.parse(text)
  } catch (err) {
    throw new Error(`Failed to parse TaskSegmentation response: ${err}. Response text: ${text}`)
  }
  if (confidence < config.segmentationThreshold) {
    await humanReviewHook({
      step: 'TaskSegmentation',
      prompt: rawPrompt,
      response: llmResponse
    })
  }
  return tasks
}