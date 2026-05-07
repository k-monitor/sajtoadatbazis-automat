<template>
    <div class="flex my-auto px-1 my-1">
        <USelectMenu class="w-44" v-model="selectedInternal" by="id" :options="buckets" @change="emit('refresh')">
            <template #option="{ option }">
                <span>{{ option.name }}</span>
            </template>
            <template #empty>betöltés...</template>
            <template #label>
                <Icon name="mdi:percent-outline" class="mr-1" />
                <span>{{ selectedInternal['name'] }}</span>
            </template>
        </USelectMenu>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const buckets = [
    { name: "Bármilyen %", id: -1, min: null, max: null },
    { name: "0–25%", id: 0, min: 0.0, max: 0.25 },
    { name: "25–50%", id: 1, min: 0.25, max: 0.5 },
    { name: "50–75%", id: 2, min: 0.5, max: 0.75 },
    { name: "75–100%", id: 3, min: 0.75, max: 1.0001 },
];

const emit = defineEmits(['update:selectedScore', 'refresh']);
const selectedInternal = ref(buckets[0]);

watch(selectedInternal, (newVal) => {
    emit('update:selectedScore', newVal);
});
</script>
