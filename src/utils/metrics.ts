import { Counter, Gauge, Histogram, Registry, collectDefaultMetrics } from 'prom-client'
import { Request, Response } from 'express'

const register = new Registry()
collectDefaultMetrics({ register })

const analysisStepLatency = new Histogram({
  name: 'analysis_step_latency_seconds',
  help: 'Latency of each analysis pipeline step in seconds',
  labelNames: ['step'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [register]
})

const schemaValidationFailures = new Counter({
  name: 'task_schema_validation_failures_total',
  help: 'Total number of task schema validation failures',
  labelNames: ['step', 'error'],
  registers: [register]
})

const tasksQueueLength = new Gauge({
  name: 'tasks_queue_length',
  help: 'Current number of tasks in the analysis queue',
  labelNames: ['topic'],
  registers: [register]
})

/**
 * Records the duration of a pipeline step.
 * @param stepName name of the analysis step
 * @param durationSeconds duration in seconds
 */
export function recordStepLatency(stepName: string, durationSeconds: number): void {
  analysisStepLatency.labels(stepName).observe(durationSeconds)
}

/**
 * Increments the schema validation failure counter.
 * @param stepName name of the validation step
 * @param errorType error identifier or message
 */
export function incSchemaValidationFailure(stepName: string, errorType: string): void {
  schemaValidationFailures.labels(stepName, errorType).inc()
}

/**
 * Sets the current length of a given queue.
 * @param topic message queue or topic name
 * @param length current number of items in queue
 */
export function setTasksQueueLength(topic: string, length: number): void {
  tasksQueueLength.labels(topic).set(length)
}

/**
 * Express handler to expose Prometheus metrics.
 */
export async function metricsHandler(req: Request, res: Response): Promise<void> {
  try {
    const metrics = await register.metrics()
    res.setHeader('Content-Type', register.contentType)
    res.status(200).send(metrics)
  } catch (err: any) {
    res.status(500).send(`Error collecting metrics: ${err.message}`)
  }
}

/**
 * Expose the Prometheus registry for advanced use.
 */
export { register as metricsRegistry, analysisStepLatency, schemaValidationFailures, tasksQueueLength }