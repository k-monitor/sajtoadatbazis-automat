<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  isOpen: boolean;
  mainArticle: any;
  groupedArticles: any[];
  groupId: number | null;
  allLabels: any;
  keywordSynonyms: any;
  allFiles: any[];
  refresh: () => void;
}>();

const emit = defineEmits<{
  (e: 'update:isOpen', value: boolean): void;
  (e: 'filter-newspaper', newspaper: { id: number; name: string }): void;
}>();

// Restructure data to match the Card component's expected format
const displayArticle = computed(() => {
  // Find the main article from the group (the one with is_main=true)
  let mainArticleToDisplay = props.mainArticle;
  let remainingArticles = [...(props.groupedArticles || [])];
  
  // Check if any of the grouped articles is marked as the main one
  const groupMainIndex = remainingArticles.findIndex((article: any) => 
    article.is_main === true || article.is_main === 1
  );
  
  if (groupMainIndex !== -1) {
    // If we found a main article in the grouped articles, use it as the display main
    mainArticleToDisplay = remainingArticles[groupMainIndex];
    // Remove it from the grouped articles and add the originally searched article to the group
    remainingArticles.splice(groupMainIndex, 1);
    remainingArticles.push(props.mainArticle);
  }
  
  // Create a copy of the main article with groupedArticles property
  return {
    ...mainArticleToDisplay,
    groupedArticles: remainingArticles
  };
});

function handleClose() {
  emit('update:isOpen', false);
}

function filterNewspaper(newspaper: { id: number; name: string }) {
  emit('filter-newspaper', newspaper);
  handleClose();
}
</script>

<template>
  <UModal 
    :model-value="isOpen" 
    @update:model-value="emit('update:isOpen', $event)"
    :ui="{ width: 'sm:max-w-6xl' }"
  >
    <div class="p-6 max-h-[80vh] overflow-y-auto">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Találat - URL alapján</h2>
        <UButton 
          icon="i-heroicons-x-mark" 
          color="gray" 
          variant="ghost" 
          @click="handleClose"
        />
      </div>

      <!-- Article with grouped articles (displayed like in the regular list) -->
      <div class="flex flex-col items-center">
        <Card
          :article="displayArticle"
          :allLabels="allLabels"
          :keywordSynonyms="keywordSynonyms"
          :allFiles="allFiles"
          :refresh="refresh"
          :is_small="false"
          @update:filter_newspaper="filterNewspaper"
          class="w-full max-w-2xl"
        />
      </div>
    </div>
  </UModal>
</template>

<style scoped>
/* Custom styling if needed */
</style>
