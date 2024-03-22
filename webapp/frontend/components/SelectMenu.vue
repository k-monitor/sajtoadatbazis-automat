<template>
    <!--  multiple by="label" option-attribute="label" @update:model-value="$emit('update:positiveList', localPositiveList)" -->

    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu 
        @close="() => $emit('update:positiveList', localPositiveList)"
        creatable :searchable="search" searchable-placeholder="Keresés..."
        class="my-2"
        v-model="localPositiveList" :options="localList" by="id" option-attribute="db_name" multiple>
        <template #label>
            <span v-if="localPositiveList.length" class="truncate">{{ localPositiveList.map((item) => item.db_name != 'null' ? item.db_name : item.name).join(', ') }}</span>
            <span v-else>Válassz ki elemeket</span>
        </template>
        <template #option-create="{ option }">
            <span class="flex-shrink-0">Új {{ type }}:</span>
            <span class="block truncate">{{ option.name }}</span>
        </template>
        <template #option="{ option }">
            <div v-if="option.db_name != 'null'">
                
                <span class="block truncate"> <Icon name="mdi:database-outline" color="green" /> {{ option.db_name }}</span>
            </div>
            <div v-else>
                <span class="block truncate">{{ option.name }}</span>
            </div>
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
            return item.name.toLowerCase().includes(q.toLowerCase())
        })
    }

    var { list, positiveList, labels, type } = defineProps(['list', 'positiveList', 'labels', 'type']);
    // Local state
    const localList = list
    console.log(localList)
    const localPositiveList = ref(positiveList);
    console.log(localPositiveList)
</script>