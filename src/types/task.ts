export interface TaskMetadata {
  priority: number
  sourceRequirementId: string
  [key: string]: any
}

export interface Task {
  id: string
  description: string
  metadata: TaskMetadata
  subtasks?: Task[]
}