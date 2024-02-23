<template>
    <USelectMenu :searchable="search" searchable-placeholder="Keresés..." trailing
        class="my-2" v-model="positiveList" :options="list" multiple>

        <template #label>
        <span v-if="positiveList.length" class="truncate">{{ positiveList.join(', ') }}</span>
        <span v-else>Válassz ki elemeket</span>
        </template>
    </USelectMenu>
</template>

<script setup lang="ts">
    function search (q: string) {
        if (q === '') {
            return list
        }

        return all.filter((item: any) => {
            return item.toLowerCase().includes(q.toLowerCase())
        })
    }

    let { data, positiveData, all, type } = defineProps(['data', 'positiveData', 'all', 'type']);
    if (data === null) {
        data = ''
    }

    if (positiveData === null) {
        positiveData = ''
    }

    var list = data.split(', ')
    var positiveList = ref(positiveData.split(', '))
</script>