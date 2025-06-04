import { createPublisher, Publisher as McpPublisher } from 'mcp-use'
import config from 'config'
import pino from 'pino'

const logger = pino({ level: config.has('log.level') ? config.get('log.level') : 'info' })

export interface Task {
  id: string
  title: string
  description: string
  dependencies: string[]
  metadata?: Record<string, any>
}

interface McpConfig {
  host: string
  port: number
  username?: string
  password?: string
  topic: string
  [key: string]: any
}

class TaskPublisher {
  private publisher: McpPublisher
  private topic: string
  private readonly maxRetries = 3
  private readonly baseRetryDelayMs = 1000
  private readonly mcpConfig: McpConfig

  constructor() {
    this.mcpConfig = config.get('mcp')
    this.topic = this.mcpConfig.topic || 'tasks.analysis'
  }

  async init(): Promise<void> {
    try {
      this.publisher = await createPublisher({
        host: this.mcpConfig.host,
        port: this.mcpConfig.port,
        username: this.mcpConfig.username,
        password: this.mcpConfig.password
      })
      logger.info({ topic: this.topic }, 'MCP publisher initialized')
    } catch (err) {
      logger.error({ err }, 'Failed to initialize MCP publisher')
      throw err
    }
  }

  async publish(tasks: Task[]): Promise<void> {
    let attempt = 0
    while (attempt < this.maxRetries) {
      try {
        await this.publisher.publish(this.topic, tasks)
        logger.info({ topic: this.topic, count: tasks.length }, 'Published tasks')
        return
      } catch (err) {
        attempt++
        logger.error({ attempt, err }, 'Publish attempt failed')
        if (attempt >= this.maxRetries) {
          logger.error('Max publish attempts reached, aborting')
          throw err
        }
        const delayMs = this.baseRetryDelayMs * attempt
        await this.delay(delayMs)
      }
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

const publisher = new TaskPublisher()
export default publisher