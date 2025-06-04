import { PromptStep, PromptContext } from '../PromptChain'
import { Task } from '../../types/task'
import { Validator } from '../../validation/Validator'
import { ValidationError } from '../../validation/ValidationError'
import { ILLMClient } from '../../llm/ILLMClient'

export class IntentExtractionStep extends PromptStep {
  private llmClient: ILLMClient
  private validator: Validator

  /**
   * @param llmClient An implementation of ILLMClient for generating completions
   * @param validator A Validator instance configured with the Task schema
   */
  constructor(llmClient: ILLMClient, validator: Validator) {
    super()
    this.llmClient = llmClient
    this.validator = validator
  }

  /**
   * Executes intent extraction by prompting the LLM with the requirement text
   * and any retrieved context, parsing the JSON response into Task objects,
   * validating them, and attaching them to the context.
   * @param ctx The current prompt context
   * @returns A new context with generatedTasks populated
   */
  async execute(ctx: PromptContext): Promise<PromptContext> {
    const prompt = this.buildPrompt(ctx.requirementText, ctx.memory)
    let raw: string
    try {
      raw = await this.llmClient.generate(prompt)
    } catch (err) {
      throw new Error(`IntentExtractionStep: LLM generation failed: ${err instanceof Error ? err.message : String(err)}`)
    }

    let parsed: any
    try {
      parsed = JSON.parse(raw)
    } catch (err) {
      throw new Error(`IntentExtractionStep: Failed to parse JSON from LLM response: ${err instanceof Error ? err.message : String(err)}\nResponse was:\n${raw}`)
    }

    if (!Array.isArray(parsed)) {
      throw new Error(`IntentExtractionStep: Expected JSON array of tasks but got: ${typeof parsed}`)
    }

    const tasks: Task[] = []
    for (const item of parsed) {
      try {
        const task = this.validator.validate<Task>(item)
        tasks.push(task)
      } catch (ve) {
        if (ve instanceof ValidationError) {
          throw new Error(`IntentExtractionStep: Task validation failed: ${ve.message}`)
        }
        throw ve
      }
    }

    return {
      ...ctx,
      generatedTasks: tasks
    }
  }

  private buildPrompt(requirement: string, memory: Array<{ id: string; text: string }>): string {
    const contextSection = memory.length
      ? `Previously seen context fragments:\n${memory.map(m => `- ${m.text}`).join('\n')}\n\n`
      : ''
    const instructions = `You are an AI assistant that extracts high-level tasks from a software requirement. Output must be valid JSON: an array of objects with fields "id" (string), "description" (string), and "metadata" (object with at least "priority" (number) and "sourceRequirementId" (string)).`
    return `${contextSection}${instructions}\n\nRequirement:\n${requirement}\n\nRespond with JSON only.`
  }
}