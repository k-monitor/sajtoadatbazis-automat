<template>
    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu creatable :searchable="search" searchable-placeholder="Keresés..." trailing
        class="my-2" v-model="positiveList2" :options="list" multiple>
        <template #label>
            <span v-if="positiveList.length" class="truncate">{{ positiveList.join(', ') }}</span>
            <span v-else>Válassz ki elemeket</span>
        </template>
        <template #option-create="{ option }">
            <span class="flex-shrink-0">Új {{ type }}:</span>
            <span class="block truncate">{{ option }}</span>
        </template>
        <template #empty>
            Nincs {{ type }}
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

    var { list, positiveList, labels, type } = defineProps(['list', 'positiveList', 'labels', 'type']);
    var positiveList2 = ref(positiveList)
</script>