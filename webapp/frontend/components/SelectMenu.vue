<template>
    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu option-attribute="name" creatable :searchable="search" searchable-placeholder="Keresés..." trailing
        class="my-2" v-model="positiveList" :options="list" multiple>
        <template #label>
            <span v-if="positiveList.length" class="truncate">{{ positiveList.map((item) => item.name).join(', ') }}</span>
            <span v-else>Válassz ki elemeket</span>
        </template>
        <template #option-create="{ option }">
            <span class="flex-shrink-0">Új {{ type }}:</span>
            <span class="block truncate">{{ option.name }}</span>
        </template>
    </USelectMenu>
</template>

<script setup lang="ts">
    function search (q: string) {
        if (q === '') {
            return list
        }

        return labels.filter((item: any) => {
            return item.toLowerCase().includes(q.toLowerCase())
        })
    }

    let { data, positiveData, labels, type } = defineProps(['data', 'positiveData', 'labels', 'type']);
    if (data === null) {
        data = ''
    }

    if (positiveData === null) {
        positiveData = ''
    }

    var list = data.split(', ')
    var positiveList = ref(positiveData.split(', ').map((item: string) => ({'name': item}) ))
    if (data === '') {
        list = []
    }
    if (positiveData === '') {
        positiveList.value = []
    }
</script>