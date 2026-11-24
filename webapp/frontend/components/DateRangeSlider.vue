<template>
  <div class="range-container">
    <div class="inputs">
      <input
        type="range"
        :value="startIndex"
        @input="
          $emit(
            'update:startIndex',
            Number(($event.target as HTMLInputElement).value)
          )
        "
        :min="0"
        :max="max-1"
        class="range-input start"
        @change="$emit('update')"
      />
      <input
        type="range"
        :value="endIndex"
        @input="
          $emit(
            'update:endIndex',
            Number(($event.target as HTMLInputElement).value)
          )
        "
        :min="0"
        :max="max-1"
        class="range-input end"
        @change="$emit('update')"
      />
    </div>
    <div class="date-labels">
      <span class="start-date-label">{{ startDate }}</span>
      <span class="end-date-label">{{ endDate }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    startIndex: number;
    endIndex: number;
    max: number;
    startDate?: string;
    endDate?: string;
  }>(),
  {
    startIndex: 0,
    endIndex: 100, // This will be overridden by the v-model binding in stats.vue
  }
);
defineEmits<{
  (e: "update:startIndex", value: number): void;
  (e: "update:endIndex", value: number): void;
  (e: "update"): void;
}>();
</script>

<style scoped>
.range-container {
  position: relative;
  width: 80%;
  margin: 20px auto;
}

.range-input {
  position: absolute;
  width: 100%;
  pointer-events: none;
  height: 0px;
  border: none;
  background: none;
}

.start {
  border-bottom: solid #000 !important;
}

.range-input::before {
  content: "";
  display: block;
  top: -1px;
  z-index: -1;
  position: absolute;
  height: 0px;
  width: 100%;
}

.range-input::-webkit-slider-thumb {
  pointer-events: auto;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #f5f5f5;
  border: #a2a2a2 1px solid;
  cursor: pointer;
  z-index: 10;
}

.range-input::-moz-range-thumb {
  pointer-events: auto;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #f5f5f5;
  border: #a2a2a2 1px solid;
  cursor: pointer;
  z-index: 10;
}

.range-input::-moz-range-track {
  background: transparent;
  border: none;
  height: 0px;
}

.inputs {
  display: flex;
}
.date-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}
</style>
