<template>
    <p style="text-transform: capitalize;"> {{ type }}: </p>
    <USelectMenu
            @close="() => $emit('update:positiveList', localPositiveList)"
            :searchable="search"
            searchable-placeholder="Keresés..."
            class="my-2"
            v-model="localPositiveList" :options="list" by="id" 
            option-attribute="name"
            creatable
            multiple
            v-model:query="query"
            @keypress="submit"
        >
        <template #label>
            <span v-if="localPositiveList.length">{{ localPositiveList.map((item) => (item.db_name != 'null' && item.db_name) ? item.db_name : item.name).join(', ') }}</span>
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
    function submit (test) {
        console.log('test')
    }
    function search (q: string) {
        if (q === '') {
            return list
        }

        return labels.filter((item: any) => {
            return item.name != null && item.name.toLowerCase().includes(q.toLowerCase())
        }).slice(0, 5).map((item: any) => {return {'id': 'db_'+item.id, 'db_id': item.id, 'name': item.name, 'db_name': item.name}})
    }

    const { list, positiveList, labels, type } = defineProps(['list', 'positiveList', 'labels', 'type']);
    const query = ref('')
    // Local state
    const localList = list
    const localPositiveList = ref(positiveList);
</script>