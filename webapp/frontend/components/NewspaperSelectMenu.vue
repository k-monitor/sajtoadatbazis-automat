<template>
    <div class="flex my-auto px-1 my-1">
        <p>Kiválasztott hírportál: &nbsp;</p>
        <USelectMenu searchable :search-attributes="['name']" searchable-placeholder="Keresés..." clear-search-on-close
            multiple class="w-48" v-model="selectedDomainsInternal" by="id" :options="allDomains"
            @change="emit('refresh')">
            <template #option="{ option }">
                <span>
                    <Icon v-if="option.has_rss" name="mdi:rss" class="text-yellow-500" />
                    {{ option.name }}
                </span>
            </template>
            <template #empty> betöltés... </template>
            <template #label>
                <span>{{
                    selectedDomainsInternal
                        .map((item) => ("name" in item ? item.name : "mind"))
                        .join(", ")
                }}</span>
            </template>
        </USelectMenu>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useSlots } from "vue";

const props = defineProps({
    allDomains: Array,
    selectedDomains: Array,
});

const emit = defineEmits(['update:selectedDomains', 'refresh']);
const selectedDomainsInternal = ref(props.selectedDomains);

watch(
    selectedDomainsInternal,
    (newVal) => {
        const mindIndex = newVal.findIndex((domain) => domain.id === -1);
        const hasOtherSelections = newVal.some((domain) => domain.id !== -1);

        if (hasOtherSelections) {
            if (mindIndex === 0)
                selectedDomainsInternal.value = newVal.filter((domain) => domain.id !== -1);
            else if (mindIndex !== -1)
                selectedDomainsInternal.value = newVal.filter((domain) => domain.id == -1);
        }

        if (!hasOtherSelections && mindIndex === -1) {
            selectedDomainsInternal.value = [{ name: "mind", id: -1 }];
        }
    },
    { immediate: true }
);

watch(selectedDomainsInternal, (newVal) => {
    emit('update:selectedDomains', newVal);
});
</script>