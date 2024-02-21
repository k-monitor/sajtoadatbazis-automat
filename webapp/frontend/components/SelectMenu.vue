<template>
    <USelectMenu class="my-2" v-model="positiveList" :options="list" multiple>
        <template #label>
        <span v-if="positiveList.length" class="truncate">{{ positiveList.join(', ') }}</span>
        <span v-else>Válassz ki elemeket</span>
        </template>
    </USelectMenu>
</template>

<script setup lang="ts">
    let { data, positiveData } = defineProps(['data', 'positiveData']);
    if (data === null) {
        data = ''
    }
    if (positiveData === null) {
        positiveData = ''
    }

    const list = data.split(', ')
    const positiveList = ref(positiveData.split(', '))
</script>