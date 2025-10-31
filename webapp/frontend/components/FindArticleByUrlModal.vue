<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
  (e: 'find-article', url: string): void;
}>();

const searchUrl = ref('');

function handleSearch() {
  if (searchUrl.value.trim()) {
    emit('find-article', searchUrl.value.trim());
    searchUrl.value = '';
  }
}

function handleClose() {
  searchUrl.value = '';
  emit('update:isOpen', false);
}
</script>

<template>
  <UModal :model-value="isOpen" @update:model-value="emit('update:isOpen', $event)">
    <div class="p-6">
      <h2 class="text-xl font-bold mb-4">Cikk keresése URL alapján</h2>
      
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2">
          Cikk URL címe:
        </label>
        <UInput
          v-model="searchUrl"
          placeholder="https://example.com/cikk-url"
          class="w-full"
          @keyup.enter="handleSearch"
        />
      </div>

      <div class="flex justify-end gap-2">
        <UButton color="gray" variant="outline" @click="handleClose">
          Mégse
        </UButton>
        <UButton 
          color="primary" 
          @click="handleSearch"
          :disabled="!searchUrl.trim()"
        >
          Keresés
        </UButton>
      </div>
    </div>
  </UModal>
</template>
