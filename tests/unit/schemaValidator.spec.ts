import { validate } from '../../../src/services/schemaValidator'

describe('schemaValidator', () => {
  it('should validate a correct task object', () => {
    const validTask = {
      id: 'task_valid_id',
      title: 'Valid Task Title',
      description: 'This is a valid description for the task.',
      dependencies: ['task_other'],
      metadata: {
        createdBy: 'unitTest',
      },
    }
    const result = validate(validTask)
    expect(result.valid).toBe(true)
    expect(result.errors).toBeUndefined()
  })

  it('should invalidate task missing required properties', () => {
    const missingPropsTask = {
      id: 'task_missing',
      // title missing
      description: 'Missing title property',
      dependencies: [],
    }
    const result = validate(missingPropsTask as any)
    expect(result.valid).toBe(false)
    expect(result.errors).toBeDefined()
    expect(result.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ message: "must have required property 'title'" }),
      ]),
    )
  })

  it('should invalidate task with invalid id pattern', () => {
    const invalidIdTask = {
      id: 'invalidId',
      title: 'Task With Bad ID',
      description: 'ID does not match required pattern.',
      dependencies: [],
    }
    const result = validate(invalidIdTask as any)
    expect(result.valid).toBe(false)
    expect(result.errors).toBeDefined()
    expect(result.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ message: 'must match pattern "^task_[a-z0-9_-]+$"' }),
      ]),
    )
  })

  it('should invalidate task with additional properties', () => {
    const extraPropsTask = {
      id: 'task_extra',
      title: 'Task With Extra Props',
      description: 'Contains an extra property not allowed by schema.',
      dependencies: [],
      extra: 'not allowed',
    }
    const result = validate(extraPropsTask as any)
    expect(result.valid).toBe(false)
    expect(result.errors).toBeDefined()
    expect(result.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ message: 'must NOT have additional properties' }),
      ]),
    )
  })

  it('should invalidate task with short title or description', () => {
    const shortFieldsTask = {
      id: 'task_short',
      title: 'Shrt',
      description: 'Too short',
      dependencies: [],
    }
    const result = validate(shortFieldsTask as any)
    expect(result.valid).toBe(false)
    expect(result.errors).toBeDefined()
    const messages = result.errors!.map(err => err.message)
    expect(messages).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/must have (minimum|at least) \d+ characters/),
      ]),
    )
  })
})