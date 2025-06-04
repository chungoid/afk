import { singleton } from 'tsyringe'
import pino, { Logger as PinoLogger, LoggerOptions } from 'pino'

const baseOptions: LoggerOptions = {
  level: process.env.LOG_LEVEL || 'info',
  base: { service: process.env.SERVICE_NAME || 'analysis-agent' },
  timestamp: pino.stdTimeFunctions.isoTime
}

const transport = process.env.NODE_ENV !== 'production'
  ? { target: 'pino-pretty', options: { colorize: true, translateTime: 'SYS:standard', ignore: 'pid,hostname' } }
  : undefined

const loggerOptions: LoggerOptions = transport
  ? { ...baseOptions, transport }
  : baseOptions

@singleton()
export class Logger {
  private logger: PinoLogger

  constructor(loggerInstance?: PinoLogger) {
    this.logger = loggerInstance || pino(loggerOptions)
  }

  debug(message: string, meta?: Record<string, unknown>) {
    this.logger.debug(meta, message)
  }

  info(message: string, meta?: Record<string, unknown>) {
    this.logger.info(meta, message)
  }

  warn(message: string, meta?: Record<string, unknown>) {
    this.logger.warn(meta, message)
  }

  error(message: string | Error, meta?: Record<string, unknown>) {
    if (message instanceof Error) {
      this.logger.error({ ...meta, stack: message.stack }, message.message)
    } else {
      this.logger.error(meta, message)
    }
  }

  child(bindings: Record<string, unknown>) {
    const childLoggerInstance = this.logger.child(bindings)
    return new Logger(childLoggerInstance)
  }
}

export const logger = new Logger()