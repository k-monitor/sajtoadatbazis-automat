<template>
  <UButton class="h-fit my-1 mx-1" :icon="sortIcon" :label="sortLabel" size="sm" color="primary" variant="outline" @click="toggleSort" />
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  reverseSort: Boolean
});

const emit = defineEmits(['update:reverseSort', 'refresh']);

const sortIcon = computed(() =>
  props.reverseSort ? 'i-heroicons-arrow-up' : 'i-heroicons-arrow-down'
);

const sortLabel = computed(() =>
  props.reverseSort ? 'Legrégebbi elől' : 'Legújabb elől'
);

function toggleSort() {
  emit('update:reverseSort', !props.reverseSort);
  emit('refresh');
}
</script>