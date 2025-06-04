import { Producer } from 'mcp-use'
import config from '../config'
import { publish_success_total, publish_failure_total } from '../metrics'
import { TaskObject } from '../validation/types'

/**
 * TaskPublisher wraps an mcp-use Producer to publish analysis tasks with
 * retry/backoff logic and a dead-letter topic for failures.
 */
export class TaskPublisher {
  private producer: Producer
  private readonly topic: string
  private readonly deadLetterTopic: string
  private readonly maxAttempts: number
  private readonly baseDelayMs: number
  private readonly factor: number
  private readonly maxDelayMs: number

  /**
   * Initialize a TaskPublisher.
   * @param producer an initialized and connected mcp-use Producer
   */
  constructor(producer: Producer) {
    this.producer = producer
    this.topic = config.topics.analysis
    this.deadLetterTopic = config.topics.deadLetter
    this.maxAttempts = config.retry.maxAttempts
    this.baseDelayMs = config.retry.baseDelayMs
    this.factor = config.retry.factor
    this.maxDelayMs = config.retry.maxDelayMs
  }

  /**
   * Publish a TaskObject to the analysis topic, retrying on transient failure.
   * If all retries fail, route the message to the dead-letter topic.
   * @param task the TaskObject to publish
   */
  async publish(task: TaskObject): Promise<void> {
    const payload = {
      topic: this.topic,
      messages: [
        {
          key: task.id,
          value: JSON.stringify(task),
        },
      ],
    }

    let attempt = 0
    let delay = this.baseDelayMs

    while (attempt < this.maxAttempts) {
      try {
        await this.producer.send(payload)
        publish_success_total.inc()
        return
      } catch (err) {
        attempt++
        publish_failure_total.inc()
        console.error(`Publish attempt ${attempt} failed for task ${task.id}`, err)

        if (attempt >= this.maxAttempts) {
          console.error(`Exceeded max attempts for task ${task.id}, routing to dead-letter topic`)
          await this.sendToDeadLetter(task)
          return
        }

        await this.sleep(delay)
        delay = Math.min(delay * this.factor, this.maxDelayMs)
      }
    }
  }

  private async sendToDeadLetter(task: TaskObject): Promise<void> {
    try {
      await this.producer.send({
        topic: this.deadLetterTopic,
        messages: [
          {
            key: task.id,
            value: JSON.stringify(task),
          },
        ],
      })
    } catch (dlqErr) {
      // If dead-letter also fails, log and give up
      console.error(`Failed to publish to dead-letter for task ${task.id}`, dlqErr)
    }
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}