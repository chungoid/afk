import dotenv from 'dotenv'
import path from 'path'

dotenv.config()

export interface Config {
  env: string
  service: {
    port: number
    metricsPort: number
    healthEndpoint: string
  }
  logLevel: string
  pinecone: {
    apiKey: string
    environment: string
    indexName: string
    topK: number
  }
  openAI: {
    apiKey: string
    baseUrl: string
    model: string
    temperature: number
    maxTokens: number
    maxRetries: number
    retryDelayMs: number
  }
  topics: {
    analysisRequest: string
    tasksAnalysis: string
    deadLetter: string
  }
  schema: {
    taskSchemaPath: string
  }
  publisher: {
    kafkaBrokers: string[]
    clientId: string
  }
}

const config: Config = {
  env: process.env.NODE_ENV || 'development',
  service: {
    port: parseInt(process.env.PORT || '3000', 10),
    metricsPort: parseInt(process.env.METRICS_PORT || '9090', 10),
    healthEndpoint: process.env.HEALTH_ENDPOINT || '/health'
  },
  logLevel: process.env.LOG_LEVEL || 'info',
  pinecone: {
    apiKey: process.env.PINECONE_API_KEY || '',
    environment: process.env.PINECONE_ENVIRONMENT || '',
    indexName: process.env.PINECONE_INDEX_NAME || 'analysis-index',
    topK: parseInt(process.env.PINECONE_TOP_K || '5', 10)
  },
  openAI: {
    apiKey: process.env.OPENAI_API_KEY || '',
    baseUrl: process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1',
    model: process.env.OPENAI_MODEL || 'gpt-4',
    temperature: parseFloat(process.env.OPENAI_TEMPERATURE || '0.7'),
    maxTokens: parseInt(process.env.OPENAI_MAX_TOKENS || '1024', 10),
    maxRetries: parseInt(process.env.OPENAI_MAX_RETRIES || '3', 10),
    retryDelayMs: parseInt(process.env.OPENAI_RETRY_DELAY_MS || '1000', 10)
  },
  topics: {
    analysisRequest: process.env.TOPIC_ANALYSIS_REQUEST || 'analysis.request',
    tasksAnalysis: process.env.TOPIC_TASKS_ANALYSIS || 'tasks.analysis',
    deadLetter: process.env.TOPIC_TASKS_DEAD_LETTER || 'tasks.analysis.deadletter'
  },
  schema: {
    taskSchemaPath: path.resolve(__dirname, '../schema/task.schema.json')
  },
  publisher: {
    kafkaBrokers: (process.env.KAFKA_BROKERS || 'localhost:9092').split(','),
    clientId: process.env.KAFKA_CLIENT_ID || 'analysis-agent'
  }
}

export default config