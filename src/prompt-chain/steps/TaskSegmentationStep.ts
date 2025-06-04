import { PromptStep } from '../PromptStep'
import { PromptContext } from '../PromptChain'
import { Task } from '../../types/task'
import { OpenAIApi, Configuration, ChatCompletionRequestMessage } from 'openai'

export class TaskSegmentationStep extends PromptStep {
  private llmClient: OpenAIApi

  constructor(apiKey?: string) {
    super()
    const configuration = new Configuration({
      apiKey: apiKey || process.env.OPENAI_API_KEY
    })
    this.llmClient = new OpenAIApi(configuration)
  }

  async execute(ctx: PromptContext): Promise<PromptContext> {
    const messages = this.buildMessages(ctx)
    let response
    try {
      response = await this.llmClient.createChatCompletion({
        model: 'gpt-4',
        messages
      })
    } catch (err) {
      throw new Error(`LLM error in TaskSegmentationStep: ${err}`)
    }
    const content = response.data.choices?.[0]?.message?.content
    if (!content) {
      throw new Error('No content received from LLM in TaskSegmentationStep')
    }
    let tasks: Task[]
    try {
      tasks = JSON.parse(content)
    } catch (err) {
      throw new Error(
        `Failed to parse JSON from LLM response in TaskSegmentationStep: ${err}\nResponse content: ${content}`
      )
    }
    return { ...ctx, generatedTasks: tasks }
  }

  private buildMessages(ctx: PromptContext): ChatCompletionRequestMessage[] {
    const messages: ChatCompletionRequestMessage[] = []
    messages.push({
      role: 'system',
      content: 'You are an assistant that segments project requirements into discrete subtasks.'
    })
    const userSections: string[] = []
    userSections.push(`Requirement:\n${ctx.requirementText}`)
    if (ctx.intent) {
      userSections.push(`Extracted Intent:\n${ctx.intent}`)
    }
    if (ctx.edgeCases && ctx.edgeCases.length) {
      userSections.push(
        `Identified Edge Cases:\n- ${ctx.edgeCases.join('\n- ')}`
      )
    }
    userSections.push(
      `Please decompose the above into a JSON array of subtasks. Each subtask must be an object with keys:
{
  "id": string,             // unique identifier
  "description": string,    // clear description
  "metadata": {
    "priority": number,
    "sourceRequirementId": string
  }
}
Return only the JSON array with no additional explanation.`
    )
    messages.push({
      role: 'user',
      content: userSections.join('\n\n')
    })
    return messages
  }
}

export default TaskSegmentationStep