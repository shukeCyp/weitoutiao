import { ref } from 'vue'

export type ToastType = 'success' | 'warning' | 'error'

export interface ToastItem {
  id: number
  message: string
  type: ToastType
  duration: number
}

const DEFAULT_DURATION: Record<ToastType, number> = {
  success: 1000,
  warning: 2000,
  error: 3000,
}

const toasts = ref<ToastItem[]>([])
let toastId = 0

const removeToast = (id: number): void => {
  toasts.value = toasts.value.filter((toast) => toast.id !== id)
}

const showToast = (message: string, type: ToastType, duration = DEFAULT_DURATION[type]): void => {
  const id = ++toastId
  toasts.value = [...toasts.value, { id, message, type, duration }]

  window.setTimeout(() => {
    removeToast(id)
  }, duration)
}

export const useToastStore = () => {
  return {
    toasts,
    showToast,
    removeToast,
  }
}
