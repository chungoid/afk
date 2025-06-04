import { ErrorObject } from "ajv"

export class ValidationError extends Error {
  public readonly errors: ErrorObject[]

  constructor(errors: ErrorObject[], message?: string) {
    super(message || "Validation failed")
    Object.setPrototypeOf(this, ValidationError.prototype)
    this.name = "ValidationError"
    this.errors = errors
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ValidationError)
    }
  }
}