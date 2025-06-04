/**
 * Represents a unit of work extracted by the Analysis Agent.
 */
export interface TaskObject {
  /**
   * Unique identifier for the task.
   */
  id: string;

  /**
   * Human-readable description of the task.
   */
  description: string;

  /**
   * Optional list of task IDs that this task depends on.
   */
  dependencies?: string[];

  /**
   * Optional metadata bag for arbitrary additional properties.
   */
  metadata?: Record<string, unknown>;

  /**
   * If any trivial type mismatches were corrected during validation,
   * this array contains the details of those corrections.
   */
  corrections?: Correction[];
}

/**
 * Details a single correction applied to a TaskObject field
 * during schema validation to coerce minor type mismatches.
 */
export interface Correction {
  /**
   * JSON pointer / path to the field that was corrected.
   */
  path: string;

  /**
   * The original value before coercion.
   */
  originalValue: unknown;

  /**
   * The value after coercion to satisfy the schema.
   */
  correctedValue: unknown;

  /**
   * Optional human-readable note describing the correction.
   */
  message?: string;
}

/**
 * Describes a non-recoverable schema validation error.
 * Emitted when a task cannot be coerced into compliance.
 */
export interface ValidationError {
  /**
   * JSON pointer / path to the field that failed validation.
   */
  path: string;

  /**
   * Detailed error message from the schema validator.
   */
  message: string;
}