import { createPublisher, Publisher } from 'mcp-use'
import config from '../config/default'
import logger from '../utils/logger'
import { incrementCounter, incrementFailureCounter } from '../utils/metrics'
import { Task } from '../validation/validator'

export class MCPPublisher {
  private publisher: Publisher
  private topic: string

  constructor() {
    this.topic = config.topics.analysisTasks
    this.publisher = createPublisher({ topic: this.topic })
  }

  /**
   * Publish a single validated task to the analysis topic.
   * @param task - The task object conforming to Task schema
   */
  async publishTask(task: Task): Promise<void> {
    const message = {
      requestId: task.metadata.requestId,
      timestamp: new Date().toISOString(),
      payload: task
    }
    try {
      await this.publisher.publish(message)
      incrementCounter('tasks_published_total', { topic: this.topic })
      logger.info('Task published successfully', { topic: this.topic, taskId: task.id })
    } catch (err) {
      incrementFailureCounter('tasks_publish_failures_total', { topic: this.topic })
      logger.error('Failed to publish task', { topic: this.topic, taskId: task.id, error: err })
      throw err
    }
  }
}

const mcpPublisher = new MCPPublisher()
export default mcpPublisher