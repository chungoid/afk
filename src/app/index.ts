import 'reflect-metadata'
import express from 'express'
import { json } from 'body-parser'
import { container } from 'tsyringe'
import config from '../config/default'
import logger from '../utils/logger'
import metrics from '../utils/metrics'
import PineconeClient from '../vector/pineconeClient'
import Retriever from '../vector/retriever'
import ChainManager from '../chain/chainManager'
import Validator from '../validation/validator'
import Publisher from '../publisher/mcpPublisher'
import AnalysisAgent from './analysisAgent'

container.registerInstance('Config', config)
container.registerInstance('Logger', logger)
container.registerInstance('Metrics', metrics)
container.register('PineconeClient', { useClass: PineconeClient })
container.register('Retriever', { useClass: Retriever })
container.register('ChainManager', { useClass: ChainManager })
container.register('Validator', { useClass: Validator })
container.register('Publisher', { useClass: Publisher })
container.register('AnalysisAgent', { useClass: AnalysisAgent })

const app = express()
app.use(json())

app.get('/health', (_req, res) => {
  res.status(200).send({ status: 'ok' })
})

app.get('/metrics', async (_req, res) => {
  try {
    const metricsPayload = await metrics.getMetrics()
    res.set('Content-Type', metrics.contentType).send(metricsPayload)
  } catch (err) {
    logger.error('Failed to collect metrics', err)
    res.status(500).send('Error collecting metrics')
  }
})

app.post(config.endpoints.analyze, async (req, res) => {
  const startTime = Date.now()
  const { requestId, text } = req.body
  if (!requestId || !text) {
    return res.status(400).json({ error: 'requestId and text are required' })
  }
  const agent = container.resolve<AnalysisAgent>('AnalysisAgent')
  try {
    const tasks = await agent.process({ requestId, text })
    res.status(200).json({ requestId, tasks })
  } catch (err) {
    logger.error(`Analysis failed for request ${requestId}`, err)
    res.status(500).json({ requestId, error: 'Analysis processing failed' })
  } finally {
    const duration = Date.now() - startTime
    metrics.observe('analysis_request_duration_ms', duration)
  }
})

const port = config.server.port || 3000
app.listen(port, () => {
  logger.info(`Analysis Agent listening on port ${port}`)
})