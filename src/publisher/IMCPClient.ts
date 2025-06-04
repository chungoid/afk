/**
 * IMCPClient defines the minimal interface for an MCP client capable of publishing messages.
 */
export interface IMCPClient {
  /**
   * Publish a message to a given topic.
   * @param topic - the destination topic name
   * @param message - the payload to be published
   * @throws Error if publishing fails
   */
  publish(topic: string, message: unknown): Promise<void>;
}