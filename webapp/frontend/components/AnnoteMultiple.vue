<template>
    <div v-if="articles && markedCount > 0" class="left-5 bottom-5 fixed z-10 my-1">
        <UButton
            color="red"
            :label="`Mindet elutasít (${markedCount})`"
            trailing-icon="i-heroicons-trash-20-solid"
            :loading="loadingDelete"
            @click="$emit('bulkDelete')"
        />
    </div>
  
    <!-- Optional hint when nothing is marked (kept minimal, not visible) -->
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    articles: Array,
    loadingDelete: Boolean,
});

defineEmits(['bulkDelete']);

// Articles marked for bulk negative annotation are those with a pending reason set
const isMarked = (article) => article && article.pending_negative_reason != null;

function countMarked(list = []) {
    let count = 0;
    for (const a of list) {
        if (!a) continue;
        if (isMarked(a)) count++;
        const children = Array.isArray(a.groupedArticles) ? a.groupedArticles : [];
        if (children.length) count += countMarked(children);
    }
    return count;
}

const markedCount = computed(() => countMarked(props.articles || []));
</script>