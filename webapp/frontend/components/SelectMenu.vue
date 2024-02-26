<template>
    <!--  multiple by="label" option-attribute="label" @update:model-value="$emit('update:positiveList', localPositiveList)" -->

    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu 
        @close="() => $emit('update:positiveList', localPositiveList)"
        creatable :searchable="search" searchable-placeholder="Keresés..."
        class="my-2"
        v-model="localPositiveList" :options="localList" by="label" option-attribute="label" multiple>
        <template #label>
            <span v-if="localPositiveList.length" class="truncate">{{ localPositiveList.map((item) => item.label).join(', ') }}</span>
            <span v-else>Válassz ki elemeket</span>
        </template>
        <template #option-create="{ option }">
            <span class="flex-shrink-0">Új {{ type }}:</span>
            <span class="block truncate">{{ option.label }}</span>
        </template>
        <template #option="{ option }">
            <span class="block truncate">{{ option.label }}</span>
        </template>
        <template #empty>
            Nincs {{ type }}
        </template>
    </USelectMenu>
</template>

<script setup lang="ts">
    function search (q: string) {
        if (q === '') {
            return list.map((item) => ({'label': item}))
        }

        return labels.filter((item: any) => {
            return item.toLowerCase().includes(q.toLowerCase())
        }).map((item) => ({'label': item}))
    }

    var { list, positiveList, labels, type } = defineProps(['list', 'positiveList', 'labels', 'type']);
    // Local state
    const localList = list.map((item) => ({'label': item}))
    console.log(localList)
    const localPositiveList = ref(positiveList);
    console.log(localPositiveList)
</script>