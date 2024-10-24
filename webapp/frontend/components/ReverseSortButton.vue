<template>
    <UButton
      class="h-fit my-1"
      :icon="sortIcon"
      size="sm"
      color="primary"
      square
      variant="solid"
      @click="toggleSort"
    />
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
  
  function toggleSort() {
    emit('update:reverseSort', !props.reverseSort);
    emit('refresh');
  }
  </script>
  