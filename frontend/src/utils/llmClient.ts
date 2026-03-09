import { resolveLlmConfig } from './modelConfig'

type ChatRole = 'system' | 'user' | 'assistant'

interface ChatMessage {
  role: ChatRole
  content: string
}

export interface LlmChatParams {
  systemPrompt: string
  prompt: string
  model?: string
  temperature?: number
  maxTokens?: number
  baseUrl?: string
  apiKey?: string
}

export interface LlmChatResult {
  content: string
  raw: unknown
}

const buildChatMessages = (systemPrompt: string, prompt: string): ChatMessage[] => {
  const messages: ChatMessage[] = []

  if (systemPrompt.trim()) {
    messages.push({ role: 'system', content: systemPrompt.trim() })
  }

  if (!prompt.trim()) {
    throw new Error('prompt 不能为空。')
  }

  messages.push({ role: 'user', content: prompt.trim() })
  return messages
}

export class LlmClient {
  async chat(params: LlmChatParams): Promise<LlmChatResult> {
    const config = await resolveLlmConfig({
      baseUrl: params.baseUrl,
      apiKey: params.apiKey,
      model: params.model,
    })
    const response = await fetch(`${config.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model,
        messages: buildChatMessages(params.systemPrompt, params.prompt),
        temperature: params.temperature,
        max_tokens: params.maxTokens,
        stream: false,
      }),
    })

    if (!response.ok) {
      throw new Error(`大模型请求失败: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    const content = data?.choices?.[0]?.message?.content

    if (typeof content !== 'string' || !content.trim()) {
      throw new Error('大模型响应中未找到有效内容。')
    }

    return {
      content,
      raw: data,
    }
  }
}

export const llmClient = new LlmClient()
