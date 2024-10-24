<template>
    <UDropdown class="left-5 bottom-5 fixed z-10 my-1" label="Elutasít" :items="items"
        :popper="{ placement: 'bottom-end' }" v-if="articles && articles.some(isSelected)">
        <UButton color="red" :label="buttonLabel" trailing-icon="i-heroicons-chevron-down-20-solid"
            :loading="loadingDelete" />
        <template #item="{ item }">
            <span>{{ item.label }}</span>
        </template>
    </UDropdown>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    articles: Array,
    items: Array,
    loadingDelete: Boolean
});

const isSelected = (article) => article.selected;

const buttonLabel = computed(() => {
    const selectedCount = props.articles.filter(isSelected).length;
    return `Kijelöltet elutasít (${selectedCount})`;
});
</script>