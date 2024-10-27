<template>
    <UModal v-model="isOpenInternal">
        <div class="p-4">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrlInternal" placeholder="https://telex.hu/..." />
            <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                <UInputMenu class="w-48" placeholder="válassz egy hírportált" v-model="selectedDomainInternal"
                    option-attribute="name" :options="domains" />
                <UButton @click="handleAddUrl">Hozzáad</UButton>
            </UContainer>
        </div>
    </UModal>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
    isOpen: Boolean,
    domains: Array
});

const emit = defineEmits(['update:isOpen', 'add-url']);

const isOpenInternal = computed({
    get: () => props.isOpen,
    set: (value) => emit('update:isOpen', value),
});

const newUrlInternal = ref("");

const selectedDomainInternal = ref(null);

function handleAddUrl() {
    const url = newUrlInternal.value;
    emit('add-url', url, selectedDomainInternal.value);
    newUrlInternal.value = "";
}
</script>
