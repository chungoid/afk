import fs from 'fs'
import path from 'path'
import Ajv, { ValidateFunction, ErrorObject } from 'ajv'
import addFormats from 'ajv-formats'
import ValidationError from './ValidationError'

/**
 * Validator wraps AJV JSON Schema validation.
 * It loads a schema from the given path, compiles it, and validates objects against it.
 */
export default class Validator {
  private validator: ValidateFunction

  /**
   * Constructs a Validator.
   * @param schemaPath - Path to a JSON Schema file.
   * @throws Error if schema file is missing or invalid JSON.
   */
  constructor(schemaPath: string) {
    const absolutePath = path.isAbsolute(schemaPath)
      ? schemaPath
      : path.resolve(__dirname, '..', schemaPath)

    if (!fs.existsSync(absolutePath)) {
      throw new Error(`Schema file not found at path: ${absolutePath}`)
    }

    let schemaContent: string
    try {
      schemaContent = fs.readFileSync(absolutePath, 'utf-8')
    } catch (err) {
      throw new Error(`Failed to read schema file at ${absolutePath}: ${err.message}`)
    }

    let schema: object
    try {
      schema = JSON.parse(schemaContent)
    } catch (err) {
      throw new Error(`Invalid JSON in schema file at ${absolutePath}: ${err.message}`)
    }

    const ajv = new Ajv({
      allErrors: true,
      strict: false,
      removeAdditional: 'all',
      useDefaults: true,
      coerceTypes: true
    })
    addFormats(ajv)

    try {
      this.validator = ajv.compile(schema)
    } catch (err) {
      throw new Error(`Failed to compile JSON schema from ${absolutePath}: ${err.message}`)
    }
  }

  /**
   * Validates the provided object against the loaded schema.
   * @param obj - The object to validate
   * @returns The validated and coerced object of type T
   * @throws ValidationError when validation fails
   */
  validate<T>(obj: any): T {
    const valid = this.validator(obj)
    if (!valid) {
      const errors: ErrorObject[] | null | undefined = this.validator.errors
      throw new ValidationError('JSON schema validation error', errors || [])
    }
    return obj as T
  }
}