import Ajv, { ValidateFunction, ErrorObject } from 'ajv'
import addFormats from 'ajv-formats'
import schema from '../config/schema/task.schema.json'

export interface ValidationResult {
  valid: boolean
  errors?: ErrorObject[] | null
}

const ajv = new Ajv({ allErrors: true, strict: false })
addFormats(ajv)

const validateFn: ValidateFunction = ajv.compile(schema)

/**
 * Validate a task object against the canonical JSON schema.
 * @param task - The object to validate
 * @returns ValidationResult containing validity and error details if invalid
 */
export function validate(task: unknown): ValidationResult {
  const valid = validateFn(task) as boolean
  return {
    valid,
    errors: valid ? undefined : validateFn.errors
  }
}

/**
 * Validate a task object and throw if invalid.
 * @param task - The object to validate
 * @returns The original task typed as T if valid
 * @throws Error with detailed schema validation messages
 */
export function validateOrThrow<T>(task: unknown): T {
  const result = validate(task)
  if (!result.valid) {
    const messages = (result.errors || [])
      .map((err) => `${err.instancePath || '/'} ${err.message}`)
      .join('; ')
    throw new Error(`Schema validation failed: ${messages}`)
  }
  return task as T
}