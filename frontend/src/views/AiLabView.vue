<script setup lang="ts">
import { computed, ref } from 'vue'

import { imageClient } from '../utils/imageClient'
import { llmClient } from '../utils/llmClient'
import { useToastStore } from '../stores/toast'

const { showToast } = useToastStore()

const activeSection = ref<'llm' | 'image' | 'titleRewrite' | 'articleRewrite'>('llm')
const systemPrompt = ref('你是一个专业、简洁、可靠的中文助手。')
const userPrompt = ref('请根据下面主题生成一段适合发布的短文案：春日通勤穿搭。')
const llmResult = ref('')
const llmRaw = ref('')
const isRunningLlm = ref(false)

const imagePrompt = ref('一只可爱的猫咪在花园里玩耍，阳光柔和，花朵盛开，高清细节。')
const imageReasoning = ref('')
const imageDataUrl = ref('')
const imageMarkdown = ref('')
const isGeneratingImage = ref(false)

const titleSource = ref('中国反制一出手，全球供应链开始重新站队。')
const rewrittenTitle = ref('')
const isRewritingTitle = ref(false)

const articleTemplateKey = ref<ArticleRewriteTemplateKey>('international_account_starter')
const articleSource = ref('美国又一次试图把盟友拽上自己的战车，但真正付出代价的，往往不是华盛顿，而是那些被裹挟的欧洲国家。表面上看是安全议题，背后其实还是产业、能源和全球话语权的再分配。')
const rewrittenArticle = ref('')
const isRewritingArticle = ref(false)
const isDownloadingArticle = ref(false)

const llmResultLines = computed(() => llmResult.value.split('\n').filter(Boolean).length)
const apiAvailable = computed(() => !!window.pywebview?.api)
const articleTemplateOptions: Array<{ key: ArticleRewriteTemplateKey; label: string; description: string }> = [
  { key: 'international_account_starter', label: '起号版', description: '适合更强调节奏和吸引力的账号起步内容。' },
  { key: 'international_stable_hardcore', label: '硬核版', description: '适合信息密度更高、观点更硬的国际内容改写。' },
  { key: 'international_stable_strategic', label: '战略版', description: '适合宏观叙事、战略分析和结构化表达。' },
]
const currentTemplateDescription = computed(
  () => articleTemplateOptions.find((item) => item.key === articleTemplateKey.value)?.description ?? '',
)

type ArticleSection = {
  key: string
  label: string
  content: string
}

const articleSections = computed<ArticleSection[]>(() => {
  const source = rewrittenArticle.value.trim()
  if (!source) {
    return []
  }

  const lines = source.split('\n')
  const sections: ArticleSection[] = []
  let currentLabel = ''
  let currentContent: string[] = []

  const pushSection = () => {
    const normalizedLabel = currentLabel.trim()
    const normalizedContent = currentContent.join('\n').trim()
    if (!normalizedLabel || !normalizedContent) {
      return
    }
    sections.push({
      key: `${normalizedLabel}-${sections.length}`,
      label: normalizedLabel,
      content: normalizedContent,
    })
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()
    const marker = line.trim()
    if (marker.startsWith('########')) {
      pushSection()
      currentLabel = marker.replace(/^########/, '').trim()
      currentContent = []
      continue
    }
    currentContent.push(line)
  }

  pushSection()

  return sections.sort((left, right) => {
    if (left.label === '导语') {
      return -1
    }
    if (right.label === '导语') {
      return 1
    }

    const leftNumber = Number.parseInt(left.label, 10)
    const rightNumber = Number.parseInt(right.label, 10)
    const leftHasNumber = Number.isFinite(leftNumber)
    const rightHasNumber = Number.isFinite(rightNumber)

    if (leftHasNumber && rightHasNumber) {
      return leftNumber - rightNumber
    }
    if (leftHasNumber) {
      return -1
    }
    if (rightHasNumber) {
      return 1
    }
    return 0
  })
})

const hasStructuredArticleSections = computed(() => articleSections.value.length > 0)

const runLlm = async (): Promise<void> => {
  if (!systemPrompt.value.trim()) {
    showToast('系统提示词不能为空。', 'warning')
    return
  }

  if (!userPrompt.value.trim()) {
    showToast('请输入用户提示词。', 'warning')
    return
  }

  isRunningLlm.value = true
  llmResult.value = ''
  llmRaw.value = ''

  try {
    const result = await llmClient.chat({
      systemPrompt: systemPrompt.value,
      prompt: userPrompt.value,
    })

    llmResult.value = result.content
    llmRaw.value = JSON.stringify(result.raw, null, 2)
    showToast('大模型调用完成。', 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '大模型调用失败。', 'error')
  } finally {
    isRunningLlm.value = false
  }
}

const runImage = async (): Promise<void> => {
  if (!imagePrompt.value.trim()) {
    showToast('请输入生图提示词。', 'warning')
    return
  }

  isGeneratingImage.value = true
  imageReasoning.value = ''
  imageDataUrl.value = ''
  imageMarkdown.value = ''

  try {
    const result = await imageClient.generate({
      prompt: imagePrompt.value,
    })

    imageReasoning.value = result.reasoning
    imageDataUrl.value = result.dataUrl
    imageMarkdown.value = result.markdown
    showToast('图片生成完成。', 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '图片生成失败。', 'error')
  } finally {
    isGeneratingImage.value = false
  }
}

const runTitleRewrite = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持标题改写。', 'warning')
    return
  }
  if (!titleSource.value.trim()) {
    showToast('请输入原标题。', 'warning')
    return
  }

  isRewritingTitle.value = true
  rewrittenTitle.value = ''
  try {
    rewrittenTitle.value = await api.rewrite_title(titleSource.value)
    showToast('标题改写完成。', 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '标题改写失败。', 'error')
  } finally {
    isRewritingTitle.value = false
  }
}

const runArticleRewrite = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持文章改写。', 'warning')
    return
  }
  if (!articleSource.value.trim()) {
    showToast('请输入待改写正文。', 'warning')
    return
  }

  isRewritingArticle.value = true
  rewrittenArticle.value = ''
  try {
    rewrittenArticle.value = await api.rewrite_article(articleSource.value, articleTemplateKey.value)
    showToast('文章改写完成。', 'success')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '文章改写失败。', 'error')
  } finally {
    isRewritingArticle.value = false
  }
}

const downloadRewrittenArticle = async (): Promise<void> => {
  const api = window.pywebview?.api
  if (!api) {
    showToast('当前环境不支持文章下载。', 'warning')
    return
  }
  if (!rewrittenArticle.value.trim()) {
    showToast('暂无可下载的改写结果。', 'warning')
    return
  }

  isDownloadingArticle.value = true
  try {
    const result = await api.download_rewritten_article(rewrittenArticle.value)
    if (result.status === 'success') {
      showToast(`文章已下载到：${result.path ?? '已选择路径'}`, 'success')
      return
    }
    if (result.status === 'cancel') {
      return
    }
    showToast(result.message ?? '文章下载失败。', 'error')
  } catch (error) {
    showToast(error instanceof Error ? error.message : '文章下载失败。', 'error')
  } finally {
    isDownloadingArticle.value = false
  }
}
</script>

<template>
  <section class="page-section ai-lab-layout">
    <header class="page-head ai-lab-head">
      <div>
        <p class="ai-lab-eyebrow">AI LAB</p>
        <h2 class="page-title">模型调试台</h2>
        <p class="page-subtitle">按功能切换调试大模型、生图、标题改写与文章改写能力，便于快速验证当前设置是否可用。</p>
      </div>
      <div class="ai-lab-badge">内部调试页</div>
    </header>

    <div class="settings-tabs ai-lab-tabs" role="tablist" aria-label="AI Lab sections">
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'llm' }" @click="activeSection = 'llm'">
        大模型调用
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'image' }" @click="activeSection = 'image'">
        生图调用
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'titleRewrite' }" @click="activeSection = 'titleRewrite'">
        标题改写
      </button>
      <button type="button" class="settings-tab" :class="{ 'settings-tab--active': activeSection === 'articleRewrite' }" @click="activeSection = 'articleRewrite'">
        文章改写
      </button>
    </div>

    <Transition name="section-fade" mode="out-in">
      <article v-if="activeSection === 'llm'" key="llm" class="ai-lab-card ai-lab-card--editorial ai-lab-card--single">
        <div class="ai-lab-card__head">
          <div>
            <h3 class="ai-lab-card__title">大模型调用</h3>
            <p class="ai-lab-card__text">支持 system prompt + user prompt，适合调试文案生成、摘要和改写。</p>
          </div>
          <span class="ai-lab-stat">{{ llmResultLines }} 行输出</span>
        </div>

        <div class="ai-lab-form">
          <label class="ai-lab-field">
            <span class="ai-lab-field__label">系统提示词</span>
            <textarea v-model="systemPrompt" class="ai-lab-textarea ai-lab-textarea--compact" placeholder="请输入系统提示词" />
          </label>

          <label class="ai-lab-field">
            <span class="ai-lab-field__label">用户提示词</span>
            <textarea v-model="userPrompt" class="ai-lab-textarea" placeholder="请输入用户提示词" />
          </label>

          <div class="ai-lab-actions">
            <button type="button" class="ai-lab-btn" :disabled="isRunningLlm" @click="runLlm">
              {{ isRunningLlm ? '调用中...' : '运行大模型' }}
            </button>
          </div>
        </div>

        <div class="ai-lab-output ai-lab-output--dual">
          <div class="ai-lab-output__block">
            <span class="ai-lab-output__label">文本结果</span>
            <pre class="ai-lab-output__content">{{ llmResult || '运行后会在这里显示模型输出。' }}</pre>
          </div>
          <div class="ai-lab-output__block">
            <span class="ai-lab-output__label">原始响应</span>
            <pre class="ai-lab-output__content ai-lab-output__content--muted">{{ llmRaw || '运行后会在这里显示原始 JSON。' }}</pre>
          </div>
        </div>
      </article>

      <article v-else-if="activeSection === 'image'" key="image" class="ai-lab-card ai-lab-card--visual ai-lab-card--single">
        <div class="ai-lab-card__head">
          <div>
            <h3 class="ai-lab-card__title">生图调用</h3>
            <p class="ai-lab-card__text">按已验证的 SSE 返回结构解析生成过程，并直接预览图片结果。</p>
          </div>
          <span class="ai-lab-stat">SSE 解析</span>
        </div>

        <div class="ai-lab-form">
          <label class="ai-lab-field">
            <span class="ai-lab-field__label">生图提示词</span>
            <textarea v-model="imagePrompt" class="ai-lab-textarea" placeholder="请输入生图提示词" />
          </label>

          <div class="ai-lab-actions">
            <button type="button" class="ai-lab-btn ai-lab-btn--accent" :disabled="isGeneratingImage" @click="runImage">
              {{ isGeneratingImage ? '生成中...' : '运行生图' }}
            </button>
          </div>
        </div>

        <div class="ai-lab-preview ai-lab-preview--single">
          <div class="ai-lab-preview__image" :class="{ 'ai-lab-preview__image--empty': !imageDataUrl }">
            <img v-if="imageDataUrl" :src="imageDataUrl" alt="生成图片预览" class="ai-lab-preview__img" />
            <span v-else>生成完成后会在这里显示图片预览</span>
          </div>

          <div class="ai-lab-output ai-lab-output--dual">
            <div class="ai-lab-output__block">
              <span class="ai-lab-output__label">生成过程</span>
              <pre class="ai-lab-output__content">{{ imageReasoning || '生成过程会显示在这里。' }}</pre>
            </div>
            <div class="ai-lab-output__block">
              <span class="ai-lab-output__label">Markdown</span>
              <pre class="ai-lab-output__content ai-lab-output__content--muted">{{ imageMarkdown || '生成完成后会在这里显示 markdown 图片内容。' }}</pre>
            </div>
          </div>
        </div>
      </article>

      <article v-else-if="activeSection === 'titleRewrite'" key="titleRewrite" class="ai-lab-card ai-lab-card--editorial ai-lab-card--single">
        <div class="ai-lab-card__head">
          <div>
            <h3 class="ai-lab-card__title">标题改写测试</h3>
            <p class="ai-lab-card__text">直接调用后端真实标题改写链路，验证 prompt、模型配置和返回结果是否正常。</p>
          </div>
          <span class="ai-lab-stat">{{ apiAvailable ? 'PyWebView API' : 'API 不可用' }}</span>
        </div>

        <div class="ai-lab-form">
          <label class="ai-lab-field">
            <span class="ai-lab-field__label">原标题</span>
            <textarea v-model="titleSource" class="ai-lab-textarea ai-lab-textarea--compact" placeholder="请输入原标题" />
          </label>

          <div class="ai-lab-actions">
            <button type="button" class="ai-lab-btn" :disabled="isRewritingTitle || !apiAvailable" @click="runTitleRewrite">
              {{ isRewritingTitle ? '改写中...' : '运行标题改写' }}
            </button>
          </div>
        </div>

        <div class="ai-lab-output">
          <div class="ai-lab-output__block">
            <span class="ai-lab-output__label">改写结果</span>
            <pre class="ai-lab-output__content">{{ rewrittenTitle || '运行后会在这里显示标题改写结果。' }}</pre>
          </div>
        </div>
      </article>

      <article v-else key="articleRewrite" class="ai-lab-card ai-lab-card--editorial ai-lab-card--single">
        <div class="ai-lab-card__head">
          <div>
            <h3 class="ai-lab-card__title">文章改写测试</h3>
            <p class="ai-lab-card__text">按选择的常量模板调用后端文章改写能力，便于测试三种改写风格。</p>
          </div>
          <span class="ai-lab-stat">模板驱动</span>
        </div>

        <div class="ai-lab-form">
          <label class="ai-lab-field">
            <span class="ai-lab-field__label">改写模板</span>
            <select v-model="articleTemplateKey" class="basic-settings-input ai-lab-select">
              <option v-for="option in articleTemplateOptions" :key="option.key" :value="option.key">{{ option.label }}</option>
            </select>
            <span class="ai-lab-field__hint">{{ currentTemplateDescription }}</span>
          </label>

          <label class="ai-lab-field">
            <span class="ai-lab-field__label">待改写正文</span>
            <textarea v-model="articleSource" class="ai-lab-textarea" placeholder="请输入待改写的文章正文" />
          </label>

          <div class="ai-lab-actions">
            <button type="button" class="ai-lab-btn" :disabled="isRewritingArticle || !apiAvailable" @click="runArticleRewrite">
              {{ isRewritingArticle ? '改写中...' : '运行文章改写' }}
            </button>
            <button type="button" class="ai-lab-btn ai-lab-btn--secondary" :disabled="isDownloadingArticle || !rewrittenArticle.trim() || !apiAvailable" @click="downloadRewrittenArticle">
              {{ isDownloadingArticle ? '下载中...' : '下载改写结果' }}
            </button>
          </div>
        </div>

        <div class="ai-lab-output">
          <div class="ai-lab-output__block">
            <span class="ai-lab-output__label">改写结果</span>
            <div v-if="hasStructuredArticleSections" class="ai-lab-article-result">
              <section v-for="section in articleSections" :key="section.key" class="ai-lab-article-section">
                <h4 class="ai-lab-article-section__title">{{ section.label }}</h4>
                <pre class="ai-lab-output__content ai-lab-output__content--article">{{ section.content }}</pre>
              </section>
            </div>
            <pre v-else class="ai-lab-output__content">{{ rewrittenArticle || '运行后会在这里显示文章改写结果。' }}</pre>
          </div>
        </div>
      </article>
    </Transition>
  </section>
</template>
