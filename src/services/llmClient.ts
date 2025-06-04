import { Configuration, OpenAIApi, ChatCompletionRequestMessage, CreateChatCompletionResponse, CreateEmbeddingResponse } from "openai"
import pino from "pino"

const logger = pino({ name: "LLMClient" })

export interface LLMClientConfig {
  apiKey: string
  model?: string
  temperature?: number
  maxTokens?: number
}

export interface LLMRequestOptions {
  model?: string
  temperature?: number
  maxTokens?: number
}

/**
 * LLMClient wraps the OpenAI API for chat completions and embeddings.
 */
export class LLMClient {
  private client: OpenAIApi
  private defaultModel: string
  private defaultTemperature: number
  private defaultMaxTokens: number

  constructor(config: LLMClientConfig) {
    if (!config.apiKey) {
      throw new Error("LLMClient requires an apiKey in the configuration")
    }
    const openaiConfig = new Configuration({ apiKey: config.apiKey })
    this.client = new OpenAIApi(openaiConfig)
    this.defaultModel = config.model || "gpt-3.5-turbo"
    this.defaultTemperature = typeof config.temperature === "number" ? config.temperature : 0.7
    this.defaultMaxTokens = typeof config.maxTokens === "number" ? config.maxTokens : 1024
    logger.info({ model: this.defaultModel, temperature: this.defaultTemperature }, "Initialized LLMClient")
  }

  /**
   * Send a chat completion request to the LLM.
   * @param messages - Array of ChatCompletionRequestMessage objects.
   * @param options - Optional per-request overrides.
   * @returns the assistant's response text.
   */
  async chat(
    messages: ChatCompletionRequestMessage[],
    options: LLMRequestOptions = {}
  ): Promise<{ text: string; usage: { promptTokens: number; completionTokens: number; totalTokens: number } }> {
    const model = options.model || this.defaultModel
    const temperature = typeof options.temperature === "number" ? options.temperature : this.defaultTemperature
    const max_tokens = typeof options.maxTokens === "number" ? options.maxTokens : this.defaultMaxTokens

    try {
      logger.debug({ model, temperature, max_tokens, messages }, "Sending chat completion request")
      const response = await this.client.createChatCompletion({
        model,
        temperature,
        max_tokens,
        messages
      })
      return this.handleChatResponse(response)
    } catch (error: any) {
      logger.error({ err: error }, "Error in chat completion")
      throw error
    }
  }

  private handleChatResponse(response: CreateChatCompletionResponse) {
    if (!response.data.choices || response.data.choices.length === 0) {
      throw new Error("LLMClient.chat: no choices returned from OpenAI")
    }
    const choice = response.data.choices[0]
    const text = choice.message?.content?.trim() || ""
    const usage = response.data.usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
    return {
      text,
      usage: {
        promptTokens: usage.prompt_tokens,
        completionTokens: usage.completion_tokens,
        totalTokens: usage.total_tokens
      }
    }
  }

  /**
   * Generate an embedding vector for the given text.
   * @param input - The text to embed.
   * @returns embedding vector as array of floats.
   */
  async embed(input: string): Promise<number[]> {
    try {
      logger.debug({ inputLength: input.length }, "Sending embedding request")
      const response: CreateEmbeddingResponse = await this.client.createEmbedding({
        model: "text-embedding-ada-002",
        input
      })
      if (!response.data.data || response.data.data.length === 0 || !response.data.data[0].embedding) {
        throw new Error("LLMClient.embed: no embedding returned")
      }
      return response.data.data[0].embedding
    } catch (error: any) {
      logger.error({ err: error }, "Error in embedding")
      throw error
    }
  }
}