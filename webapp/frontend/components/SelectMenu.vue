<template>
    <!--  multiple by="label" option-attribute="label" @update:model-value="$emit('update:positiveList', localPositiveList)" -->

    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu
            @close="() => $emit('update:positiveList', localPositiveList)"
            :searchable="search"
            searchable-placeholder="Keresés..."
            class="my-2"
            v-model="localPositiveList" :options="localList" by="id" 
            creatable
            multiple
        >
        <template #label>
            <span v-if="localPositiveList.length" class="truncate">{{ localPositiveList.map((item) => item.db_name != 'null' ? item.db_name : item.name).join(', ') }}</span>
            <span v-else>Válassz ki elemeket</span>
        </template>
        <template #option-create="{ option }">
            <span class="flex-shrink-0">Új {{ type }}:</span>
            <span class="block truncate">{{ option.name }}</span>
        </template>
        <template #option="{ option }">
                <span class="block truncate"> <Icon v-if="option.db_name != 'null'" name="mdi:database-outline" color="green" /> {{ option.db_name != 'null' ? option.db_name : option.name }}  {{option.classification_score != null ? '('+(option.classification_score*100).toFixed(0)+'%' : ''}} <Icon v-if="option.classification_label == 1 && option.classification_score != null" name="mdi:emoticon-devil" color="red"/> <Icon v-else-if="option.classification_score != null" name="mdi:account-cowboy-hat" color="gold" /> {{ option.classification_score != null ? ')' : '' }} </span>
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
            return item.name != null && item.name.toLowerCase().includes(q.toLowerCase())
        }).slice(0, 5).map((item: any) => {return {'id': item.id, 'name': item.name, 'db_name': item.name}})
    }

    const props = defineProps(['list', 'positiveList', 'labels', 'type']);
    var { list, positiveList, type } = props;
    const {labels} = props;
    // Local state
    const localList = list
    const localPositiveList = ref(positiveList);
</script>