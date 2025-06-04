import { inject, injectable } from 'tsyringe'
import Ajv, { ValidateFunction, ErrorObject } from 'ajv'
import addFormats from 'ajv-formats'
import schema from '../schema/task.schema.json'
import { Logger } from '../utils/logger'

export class ValidationError extends Error {
  public readonly errors: string[]
  constructor(message: string, errors: string[]) {
    super(message)
    this.name = 'ValidationError'
    this.errors = errors
  }
}

/**
 * Validator wraps AJV JSON Schema validation for Task objects.
 * It compiles the task schema once at startup and exposes a method
 * to validate arbitrary objects against the schema, throwing on failure.
 */
@injectable()
export class Validator {
  private ajv: Ajv
  private validateFn: ValidateFunction

  constructor(@inject(Logger) private logger: Logger) {
    this.ajv = new Ajv({ allErrors: true, strict: false })
    addFormats(this.ajv)
    this.validateFn = this.ajv.compile(schema)
    this.logger.debug('Validator initialized with Task schema')
  }

  /**
   * Validates the given object against the Task schema.
   * @param taskPayload arbitrary object to validate
   * @throws ValidationError if the payload does not conform to the schema
   */
  public validateTask(taskPayload: unknown): void {
    const valid = this.validateFn(taskPayload)
    if (!valid) {
      const errors = this.formatErrors(this.validateFn.errors || [])
      this.logger.error('Task schema validation failed', { errors })
      throw new ValidationError('Invalid Task payload', errors)
    }
    this.logger.debug('Task payload passed schema validation')
  }

  private formatErrors(ajvErrors: ErrorObject[]): string[] {
    return ajvErrors.map(err => {
      const path = err.instancePath || err.schemaPath || ''
      const msg = err.message || 'validation error'
      return `${path} ${msg}`.trim()
    })
  }
}