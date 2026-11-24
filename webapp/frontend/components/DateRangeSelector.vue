<template>
  <UPopover class="px-1" :popper="{ placement: 'bottom-start' }">
    <UButton icon="i-heroicons-calendar-days-20-solid" class=" my-1">
      {{ format(selected.start, "yyyy. MM. dd.") }} -
      {{ format(selected.end, "yyyy. MM. dd.") }}
    </UButton>

    <template #panel="{ close }">
      <div class="flex items-center sm:divide-x divide-gray-200 dark:divide-gray-800">
        <div class="hidden sm:flex flex-col py-4">
          <UButton v-for="(range, index) in ranges" :key="index" :label="range.label" color="gray" variant="ghost"
            class="rounded-none px-6" :class="[
              isRangeSelected(range.duration)
                ? 'bg-gray-100 dark:bg-gray-800'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
            ]" truncate @click="selectRange(range.duration)" />
        </div>

        <DatePicker v-model="selectedInternal" is-required @close="() => closeAndRefresh(close)" />
      </div>
    </template>
  </UPopover>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { sub, format, isSameDay } from "date-fns";

const props = defineProps({
  selected: Object,
  ranges: Array
});

const emit = defineEmits(['update:selected', 'refresh']);
const selectedInternal = ref(props.selected);

function selectRange(duration) {
  const start = sub(new Date(), duration);
  const end = new Date();
  selectedInternal.value = { start, end };
}

function isRangeSelected(duration) {
  return (
    isSameDay(selectedInternal.value.start, sub(new Date(), duration)) &&
    isSameDay(selectedInternal.value.end, new Date())
  );
}

watch(selectedInternal, (newSelected) => {
  emit('update:selected', newSelected);
});

function closeAndRefresh(close) {
  close();
  emit('refresh');
}
</script>