import { PromptStep, PromptContext } from './PromptStep'
import { Task } from '../types/task'

/**
 * Orchestrates a series of PromptSteps to transform a raw requirement into structured Tasks.
 */
export class PromptChain {
  private steps: PromptStep[]

  /**
   * Creates a new PromptChain.
   * @param steps - An ordered array of PromptStep instances
   */
  constructor(steps: PromptStep[]) {
    if (!Array.isArray(steps) || steps.length === 0) {
      throw new Error('PromptChain requires at least one PromptStep')
    }
    this.steps = steps
  }

  /**
   * Executes each step in sequence, passing along a shared context.
   * @param requirementText - Raw requirement text to process
   * @returns An array of generated Task objects
   */
  async run(requirementText: string): Promise<Task[]> {
    if (typeof requirementText !== 'string' || requirementText.trim() === '') {
      throw new Error('requirementText must be a non-empty string')
    }

    let context: PromptContext = {
      requirementText,
      memory: [],
      generatedTasks: []
    }

    for (const step of this.steps) {
      try {
        context = await step.execute(context)
      } catch (err) {
        throw new Error(`Error in step ${step.constructor.name}: ${(err as Error).message}`)
      }
    }

    if (!Array.isArray(context.generatedTasks)) {
      throw new Error('PromptChain did not produce any tasks')
    }

    return context.generatedTasks
  }
}