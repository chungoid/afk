import { injectable, inject } from "tsyringe"
import { Retriever } from "../vector/retriever"
import { IntentExtractor } from "./step1_intent"
import { EdgeCaseExtractor } from "./step2_edgecases"
import { TaskDecomposer } from "./step3_decompose"
import { Validator } from "../validation/validator"
import { Publisher } from "../publisher/mcpPublisher"
import { logger } from "../utils/logger"
import { metrics } from "../utils/metrics"

export interface AnalysisRequest {
  id: string
  text: string
}

@injectable()
export class ChainManager {
  constructor(
    @inject(Retriever) private retriever: Retriever,
    @inject(IntentExtractor) private intentExtractor: IntentExtractor,
    @inject(EdgeCaseExtractor) private edgeCaseExtractor: EdgeCaseExtractor,
    @inject(TaskDecomposer) private taskDecomposer: TaskDecomposer,
    @inject(Validator) private validator: Validator,
    @inject(Publisher) private publisher: Publisher
  ) {}

  public async processRequest(request: AnalysisRequest): Promise<void> {
    const startTime = Date.now()
    logger.info({ requestId: request.id, msg: "Starting analysis chain" })
    metrics.increment("chain_requests_total")

    try {
      metrics.startTimer("chain_retrieve_duration_ms")
      const contextDocs = await this.retriever.getRelevantContext(request.text)
      metrics.endTimer("chain_retrieve_duration_ms")

      logger.debug({ requestId: request.id, step: "retrieve", contextCount: contextDocs.length })

      metrics.startTimer("chain_intent_duration_ms")
      const intent = await this.intentExtractor.extractPrimaryIntent(request.text, contextDocs)
      metrics.endTimer("chain_intent_duration_ms")
      logger.debug({ requestId: request.id, step: "intent", intent })

      metrics.startTimer("chain_edgecases_duration_ms")
      const edgeCases = await this.edgeCaseExtractor.extractEdgeCases(intent, contextDocs)
      metrics.endTimer("chain_edgecases_duration_ms")
      logger.debug({ requestId: request.id, step: "edgeCases", edgeCases })

      metrics.startTimer("chain_decompose_duration_ms")
      const rawTasks = await this.taskDecomposer.decompose(intent, edgeCases, contextDocs)
      metrics.endTimer("chain_decompose_duration_ms")
      logger.debug({ requestId: request.id, step: "decompose", rawTasksCount: rawTasks.length })

      const publishPromises = rawTasks.map(async task => {
        const valid = this.validator.validate("Task", task)
        if (!valid) {
          metrics.increment("validation_failures_total")
          logger.error({ requestId: request.id, task, errors: this.validator.errors })
          // optionally dead-letter or skip
          return
        }
        const enriched = { ...task, metadata: { requestId: request.id, timestamp: new Date().toISOString() } }
        await this.publisher.publish(enriched)
        metrics.increment("tasks_published_total")
        logger.info({ requestId: request.id, taskId: task.id, msg: "Published task" })
      })

      await Promise.all(publishPromises)

      const duration = Date.now() - startTime
      metrics.observe("chain_total_duration_ms", duration)
      logger.info({ requestId: request.id, duration, msg: "Analysis chain complete" })
    } catch (err) {
      metrics.increment("chain_errors_total")
      logger.error({ requestId: request.id, err, msg: "Analysis chain failed" })
      // handle dead-letter or retries at a higher level
      throw err
    }
  }
}