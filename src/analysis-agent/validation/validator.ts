import Ajv from "ajv"
import addFormats from "ajv-formats"
import schema from "./tasks.schema.json"
import { TaskObject, ValidationError } from "./types"

const ajv = new Ajv({
  allErrors: true,
  strict: false,
  coerceTypes: true,
  useDefaults: true
})
addFormats(ajv)
const validateFn = ajv.compile<TaskObject>(schema)

/**
 * Retrieves a nested value from an object given a JSON Pointer style path.
 */
function getDataByPath(obj: any, path: string): any {
  if (!path) return obj
  // AJV instancePath uses JSON Pointer format: /field/subfield/0
  const parts = path.replace(/^\//, "").split("/").map(p => p.replace(/~1/g, "/").replace(/~0/g, "~"))
  return parts.reduce((acc: any, key: string) => {
    if (acc === undefined || acc === null) return acc
    // numeric index?
    const idx = /^\d+$/.test(key) ? Number(key) : key
    return acc[idx]
  }, obj)
}

/**
 * Validates and coerces a TaskObject according to the JSON schema.
 * Returns validated (and possibly corrected) task and any corrections,
 * or validation errors if non-recoverable.
 */
export function validateTask(
  input: any
): { valid: true; task: TaskObject; errors?: ValidationError[] }
   | { valid: false; errors: ValidationError[] } {
  // deep clone so coercions don't mutate caller’s object
  const data = JSON.parse(JSON.stringify(input))
  const valid = validateFn(data)
  const errors: ValidationError[] = []

  if (!valid && validateFn.errors) {
    for (const err of validateFn.errors) {
      const path = err.instancePath || err.dataPath || ""
      const message = err.message || "Validation error"
      if (err.keyword === "type" && err.params && err.params.type) {
        const original = getDataByPath(input, path)
        const corrected = getDataByPath(data, path)
        errors.push({
          path,
          message: `Type mismatch: expected ${ (err.params as any).type }`,
          oldValue: original,
          newValue: corrected
        })
      } else {
        errors.push({ path, message })
      }
    }
  }

  // Determine if any error is non-coercible (no oldValue/newValue)
  const nonRecoverable = errors.some(e => e.oldValue === undefined && e.newValue === undefined)

  if ((valid && errors.length === 0) || (errors.length > 0 && !nonRecoverable)) {
    return {
      valid: true,
      task: data as TaskObject,
      errors: errors.length ? errors : undefined
    }
  } else {
    return { valid: false, errors }
  }
}