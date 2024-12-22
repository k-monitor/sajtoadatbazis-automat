<template>
    <div class="flex my-auto px-1 my-1">
        <USelectMenu class="w-48" v-model="selectedReasonInternal" by="id" :options="reasons" @change="emit('refresh')">
            <template #option="{ option }">
                <span>
                    {{ option.name }}
                </span>
            </template>
            <template #empty> betöltés... </template>
            <template #label>
                <span>{{
                    selectedReasonInternal['name']
                    }}</span>
            </template>
        </USelectMenu>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
    reasons: Array,
});

const emit = defineEmits(['update:selectedReason', 'refresh']);
const selectedReasonInternal = ref({ name: "Bármilyen ok", id: -1 });

watch(
    selectedReasonInternal,
    (newVal) => {
        selectedReasonInternal.value = newVal;
        emit('update:selectedReason', newVal);
    }
);
</script>