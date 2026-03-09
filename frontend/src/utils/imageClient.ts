import { resolveImageConfig } from './modelConfig'

interface StreamChunkChoice {
  delta?: {
    reasoning_content?: string
    content?: string
  }
  finish_reason?: string | null
}

interface StreamChunk {
  choices?: StreamChunkChoice[]
}

export interface GenerateImageParams {
  prompt: string
  model?: string
  baseUrl?: string
  apiKey?: string
}

export interface GenerateImageResult {
  markdown: string
  dataUrl: string
  mimeType: string
  base64: string
  reasoning: string
  rawContent: string
}

const extractImageData = (rawContent: string): { markdown: string; dataUrl: string; mimeType: string; base64: string } => {
  const markdownMatch = rawContent.match(/!\[[^\]]*\]\((data:image\/[a-zA-Z0-9.+-]+;base64,[^)]+)\)/)
  if (!markdownMatch) {
    throw new Error('生图响应中未找到 base64 图片数据。')
  }

  const dataUrl = markdownMatch[1]
  const dataUrlMatch = dataUrl.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$/)
  if (!dataUrlMatch) {
    throw new Error('图片 data URL 格式不正确。')
  }

  return {
    markdown: markdownMatch[0],
    dataUrl,
    mimeType: dataUrlMatch[1],
    base64: dataUrlMatch[2],
  }
}

const parseSsePayload = (buffer: string): { events: string[]; rest: string } => {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const parts = normalized.split('\n\n')
  const rest = parts.pop() ?? ''
  return { events: parts, rest }
}

export class ImageClient {
  async generate(params: GenerateImageParams): Promise<GenerateImageResult> {
    if (!params.prompt.trim()) {
      throw new Error('prompt 不能为空。')
    }

    const config = await resolveImageConfig({
      baseUrl: params.baseUrl,
      apiKey: params.apiKey,
      model: params.model,
    })

    const endpoint = `${config.baseUrl}/chat/completions`

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model,
        messages: [
          {
            role: 'user',
            content: params.prompt.trim(),
          },
        ],
        stream: true,
      }),
    })

    if (!response.ok) {
      throw new Error(`生图请求失败: ${response.status} ${response.statusText}`)
    }

    if (!response.body) {
      throw new Error('生图响应不支持流式读取。')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let reasoning = ''
    let rawContent = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parsed = parseSsePayload(buffer)
      buffer = parsed.rest

      for (const event of parsed.events) {
        const lines = event
          .split('\n')
          .map((line) => line.trim())
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())

        for (const payload of lines) {
          if (!payload || payload === '[DONE]') continue

          let chunk: StreamChunk
          try {
            chunk = JSON.parse(payload) as StreamChunk
          } catch {
            continue
          }

          const delta = chunk.choices?.[0]?.delta
          if (delta?.reasoning_content) reasoning += delta.reasoning_content
          if (delta?.content) rawContent += delta.content
        }
      }
    }

    buffer += decoder.decode()
    if (buffer.trim()) {
      const parsed = parseSsePayload(buffer)
      for (const event of parsed.events) {
        const lines = event
          .split('\n')
          .map((line) => line.trim())
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())

        for (const payload of lines) {
          if (!payload || payload === '[DONE]') continue

          let chunk: StreamChunk
          try {
            chunk = JSON.parse(payload) as StreamChunk
          } catch {
            continue
          }

          const delta = chunk.choices?.[0]?.delta
          if (delta?.reasoning_content) reasoning += delta.reasoning_content
          if (delta?.content) rawContent += delta.content
        }
      }
    }

    const image = extractImageData(rawContent)

    return {
      ...image,
      reasoning: reasoning.trim(),
      rawContent,
    }
  }
}

export const imageClient = new ImageClient()
