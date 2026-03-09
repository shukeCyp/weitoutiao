<script setup lang="ts">
import { useToastStore } from '../stores/toast'

const { toasts, removeToast } = useToastStore()
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack">
      <TransitionGroup name="toast-slide">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-item"
          :class="[`toast-item--${toast.type}`]"
        >
          <div class="toast-item__content">
            <span class="toast-item__message">{{ toast.message }}</span>
            <button type="button" class="toast-item__close" @click="removeToast(toast.id)">
              ×
            </button>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  pointer-events: auto;
  min-width: 240px;
  max-width: 380px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  overflow: hidden;
}

.toast-item--success {
  border-color: color-mix(in srgb, var(--success), transparent 60%);
  background: color-mix(in srgb, var(--surface), transparent 0%);
}

.toast-item--warning {
  border-color: color-mix(in srgb, var(--warning), transparent 60%);
}

.toast-item--error {
  border-color: color-mix(in srgb, var(--danger), transparent 60%);
}

.toast-item__content {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
}

.toast-item__message {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--textPrimary);
}

.toast-item--success .toast-item__message {
  color: var(--success);
}

.toast-item--warning .toast-item__message {
  color: var(--warning);
}

.toast-item--error .toast-item__message {
  color: var(--danger);
}

.toast-item__close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--textSecondary);
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  padding: 0;
}

.toast-item__close:hover {
  background: var(--surfaceElevated);
  color: var(--textPrimary);
}

/* TransitionGroup animations */
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 220ms ease;
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.toast-slide-move {
  transition: transform 220ms ease;
}
</style>
