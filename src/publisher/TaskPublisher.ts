import { IMCPClient } from './IMCPClient'
import { Task } from '../types/task'

export class TaskPublisher {
  private readonly client: IMCPClient
  private readonly topic: string = 'tasks.analysis'

  /**
   * Constructs a TaskPublisher.
   * @param mcpClient An MCP client implementing the IMCPClient interface
   */
  constructor(mcpClient: IMCPClient) {
    if (!mcpClient || typeof mcpClient.publish !== 'function') {
      throw new Error('Invalid IMCPClient provided to TaskPublisher')
    }
    this.client = mcpClient
  }

  /**
   * Publishes an array of tasks to the configured topic.
   * @param tasks Array of Task objects to publish
   * @throws Error if publishing fails
   */
  async publish(tasks: Task[]): Promise<void> {
    if (!Array.isArray(tasks)) {
      throw new Error('Tasks to publish must be an array')
    }
    if (tasks.length === 0) {
      console.warn(`[TaskPublisher] No tasks to publish to topic "${this.topic}".`)
      return
    }
    try {
      await this.client.publish(this.topic, { tasks })
      console.info(`[TaskPublisher] Successfully published ${tasks.length} tasks to topic "${this.topic}".`)
    } catch (err) {
      console.error(`[TaskPublisher] Error publishing tasks to topic "${this.topic}":`, err)
      throw err
    }
  }
}