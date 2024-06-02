<template>
    <div class="p-4">
        <div class="max-w-md rounded overflow-hidden shadow-lg mb-4 p-4">
            <p>
                <a :href="article.url" target="_blank" class="font-bold text-xl mb-2">{{ article.title }}</a>
                <UBadge class="m-1" color="gray">
                <Icon size="1.5em" v-if="article.skip_reason > 1" name="mdi:alert-circle-outline" color="orange" />
                <Icon size="1.5em" v-else-if="article.processing_step < 4" name="mdi:database-clock-outline" color="gray" />
                <Icon size="1.5em" v-else-if="article.annotation_label == null" name="mdi:question-mark" color="gray" />
                <Icon size="1.5em" v-else-if="article.annotation_label == 0" name="mdi:database-remove-outline" color="red" />
                <Icon size="1.5em" v-else-if="article.annotation_label == 1" name="mdi:database-check-outline" color="green" />
                </UBadge>
            </p>
            <UBadge class="m-1" color="blue"> {{ article.newspaper_name }} </UBadge>
            <UBadge v-if="article.source == 1" class="m-1" color="orange"> manuálisan hozzáadott </UBadge>
            <p class="text-base text-pretty">{{ article.description }}</p>
            <p class="text-base text-right py-1">{{ article.date }}</p>
            <UButton v-if="article.skip_reason > 1" color="grey" @click="retryArticle">Újra</UButton>
            <UContainer v-else-if="article.processing_step >= 4 " class="flex justify-between px-0 sm:px-0 lg:px-0">
                <UButtonGroup size="sm" orientation="horizontal">
                    <UButton v-if="article.annotation_label != 0" color="red" @click="deleteArticle">{{ article.annotation_label == null ? "Elutasít" : "Mégis elutasít" }}</UButton>
                    <UDropdown :items="items" :popper="{ placement: 'bottom-end' }">
                        <UButton color="white" label="" trailing-icon="i-heroicons-chevron-down-20-solid" />
                        <template #item="{ item }">
                            <span class="">{{ item.label }}</span>
                        </template>
                    </UDropdown>
                </UButtonGroup>
                <UButton v-if="true" @click="openModal" :loading="isOpening" class="ml-auto">{{ article.annotation_label == null ? "Tovább" : article.annotation_label == 0 ? "Mégis elfogad" : "Szerkeszt" }}</UButton>
            </UContainer>
        </div>
        <UModal v-model="isOpen" :ui="{ width: 'sm:max-w-7xl' }">
            <div class="p-4 w-full">
                <div  class="my-2 flex justify-between px-0 sm:px-0 lg:px-0 flex-wrap:wrap">
                    <div class="max-w-2xl mx-4 flex-grow">
                        <p>Cím:</p>
                        <UInput class="my-2" v-model="article.title"/>
                        <p>URL:</p>
                        <UInput class="my-2" v-model="article.url"/>
                        <p>Leírás:</p>
                        <UTextarea class="my-2" v-model="article.description"/>
                        <div class="flex justify-between">
                            <p>Szöveg:</p>
                            <div class="flex items-center">
                                <p>szerkeszt: </p><UToggle class="m-2" size="md" color="primary" v-model="edit" />
                            </div>
                        </div>
                        <UTextarea v-if="edit" class="my-2" v-model="article.text" rows="20" />
                        <div v-if="!edit" style="overflow-y: scroll; height:400px;">
                            <span class="my-2" v-html="richText"></span>
                        </div>
                    </div>

                    <div class="max-w-lg mx-4 flex-grow">
                        <SelectMenu :list="allPersons" type="személy" :creatable="true" :positive-list="positivePersons" @update:positiveList="updatePositivePersons" :labels="allLabels['person']" />
                        <SelectMenu :list="allInstitutions" type="intézmény" :creatable="true" :positive-list="positiveInstitutions" @update:positiveList="updatePositiveInstitutions" :labels="allLabels['institution']" />
                        <SelectMenu :list="allPlaces" type="helyszín" :creatable="false" :positive-list="positivePlaces" @update:positiveList="updatePositivePlaces" :labels="allLabels['place']" />
                        <SelectMenu :list="article.others" type="egyéb" :creatable="false" :positive-list="positiveOthers" @update:positiveList="updatePositiveOthers" :labels="allLabels['keywords']" />
                        <p>publikálás: {{ article.article_date }}</p>
                        <p>{{errorText}}</p>
                    </div>

                </div>
                <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                    <UButton color="gray" @click="closeModal">Mégse</UButton>

                    <div class="my-2 flex justify-between">
                        <UButtonGroup size="sm" orientation="horizontal">
                            <UButton v-if="article.annotation_label != 0" color="red" @click="deleteArticle">{{ article.annotation_label == null ? "Elutasít" : "Mégis elutasít" }}</UButton>
                            <UDropdown :items="items" :popper="{ placement: 'bottom-end' }">
                                <UButton color="white" label="" trailing-icon="i-heroicons-chevron-down-20-solid" />
                                <template #item="{ item }">
                                    <span class="">{{ item.label }}</span>
                                </template>
                            </UDropdown>
                        </UButtonGroup>
                        <UCheckbox class="mx-5" size="xl" v-model="is_active"  label="Aktív" />
                        <UButton @click="submitArticle" :loading="submitted">Elfogad</UButton>
                    </div>
                </UContainer>

            </div>
        </UModal>

    </div>
</template>

<script setup lang="ts">
    var baseUrl = 'https://autokmdb.deepdata.hu/autokmdb'
    // baseUrl = 'http://127.0.0.1:8000'
    //baseUrl = 'http://localhost:5000'
    const edit = ref(false)
    const items = [
    [
        {
            label: 'Átvett',
            slot: 'item',
            click: async () => {
            await postUrl(baseUrl+'/api/annote/negative', {
                method: 'POST',
                body: {'id': article.value.id, 'reason': 1},
            });
            refresh()},
        },
        {
            label: 'Külföldi',
            slot: 'item',
            click: async () => {
            await postUrl(baseUrl+'/api/annote/negative', {
                method: 'POST',
                body: {'id': article.value.id, 'reason': 2},
            });
            refresh()},
        },
        {
            label: 'Egyéb',
            slot: 'item',
            click: async () => {
            await postUrl(baseUrl+'/api/annote/negative', {
                method: 'POST',
                body: {'id': article.value.id, 'reason': 100},
            });
            refresh()},
        },
    ]
    ]

    async function postUrl(url, data) {
        return await $fetch(url, data)
    }

    let allPersons = ref([]);
    let allInstitutions = ref([]);
    let allPlaces = ref([]);

    let positivePersons = ref([])
    let positiveInstitutions = ref([])
    let positivePlaces = ref([])
    let positiveOthers = ref([])

    function mapEntities(entities) {
        const entitiesMap = {};
        for (const entity of entities) {
            if (entitiesMap[entity.db_id])
                entitiesMap[entity.db_id].push({ ...entity });
            else
                entitiesMap[entity.db_id] = [{ ...entity }];
        }

        const mappedEntities = [];
        for (const id in entitiesMap) {
            let entityList = entitiesMap[id];
            if (id != null) {
                let entity = { ...entityList[0] };
                entity['list'] = [...entityList];
                mappedEntities.push({ ...entity });
            } else {
                for (const entity of entityList) {
                    entity['list'] = [{ ...entity }];
                    mappedEntities.push({ ...entity });
                }
            }
        }
        return mappedEntities;
    }

    function openModal() {
        isOpening.value = true
        if (article.value.isDownloaded) {
            isOpen.value = true
            isOpening.value = false
        } else {
            $fetch(baseUrl+'/api/article/'+article.value.id, {
                query: {},
                onResponse({ request, response, options }) {
                    console.log(response._data)
                    article.value = response._data
                    allPersons.value = mapEntities(article.value.persons)
                    allInstitutions.value = mapEntities(article.value.institutions)
                    allPlaces.value = mapEntities(article.value.places)
                    article.value.date = new Date(Date.parse(article.value.date)).toLocaleString()
                    article.value.article_date = new Date(Date.parse(article.value.article_date)).toLocaleString()

                    positivePersons.value = allPersons.value.filter((person) => (person.classification_label == 1 || person.annotation_label == 1))
                    positiveInstitutions.value = allInstitutions.value.filter((institution) => (institution.classification_label == 1 || institution.annotation_label == 1))
                    positivePlaces.value = allPlaces.value.filter((place) => (place.classification_label == 1 || place.annotation_label == 1) && place.db_id)
                    positiveOthers.value = article.value.others.map((other) => (other.classification_label == 1 || other.annotation_label == 1) && other.db_id)

                    richText.value = getRichText()
                    isOpen.value = true
                    isOpening.value = false
                    article.value.isDownloaded = true
                }},
            )
        }
    }
    function closeModal() {
        isOpen.value = false
    }

    const { article: articleValue, allLabels, refresh } = defineProps(['article', 'allLabels', 'refresh']);
    const article = ref(articleValue)
    article.value.text = ''
    article.value.institutions = []
    article.value.persons = []
    article.value.places = []
    article.value.others = []
    article.value.isDownloaded = false

    const is_active = ref(true)
    let submitted = ref(false)
    let errorText = ref('')

    async function retryArticle() {
        // TODO
    }
    async function deleteArticle() {
        await postUrl(baseUrl+'/api/annote/negative', {
            method: 'POST',
            body: {'id': article.value.id, 'reason': 0},
        });
        refresh()
    }
    async function submitArticle() {
        submitted.value = true

        let positivePersonsList = positivePersons.value.map((person) => person.list ?? person).flat()
        positivePersonsList.forEach(element => {
            element.annotation_label = 1
        });

        let positiveInstitutionsList = positiveInstitutions.value.map((institution) => institution.list ?? institution).flat()
        positiveInstitutionsList.forEach(element => {
            element.annotation_label = 1
        });

        let positivePlacesList = positivePlaces.value.map((place) => place.list ?? place).flat()
        positivePlacesList.forEach(element => {
            element.annotation_label = 1
        });

        try {
            await postUrl(baseUrl+'/api/annote/positive', {
                method: 'POST',
                body: {
                    'id': article.value.id,
                    'newspaper_id': article.value.newspaper_id,
                    'url': article.value.url,
                    'title': article.value.title,
                    'description': article.value.description,
                    'text': article.value.text,
                    'positive_persons': positivePersonsList,
                    'positive_institutions': positiveInstitutions.value,
                    'positive_places': positivePlaces.value,
                    'category': article.value.category,
                    'tags': positiveOthers.value,
                    'active': is_active.value,
                },

                onResponse({ request, response, options }) {
                    submitted.value = false
                    if (response.status >= 300) {
                        errorText.value = '\n'+response.status+' Hiba: ' + response._data.error
                        return
                    }
                    refresh()
                    isOpen.value = false
                    submitted.value = false
                },
            });
        } catch (error) {
                submitted.value = false
                console.log(error)
                errorText.value = error
            }
        }
    const isOpen = ref(false)
    const isOpening = ref(false)

    article.value.date = new Date(Date.parse(article.value.date)).toLocaleString()
    article.value.article_date = new Date(Date.parse(article.value.article_date)).toLocaleString()

    function getRichText() {
        let texthtml = article.value.text
        
        let allPersons = article.value.persons.map((person) => person.list ?? [person]).flat();
        allPersons.forEach(element => {element.etype = 'person'})

        let allInstitutions = article.value.institutions.map((person) => person.list ?? [person]).flat();
        allInstitutions.forEach(element => {element.etype = 'institution'})

        let allPlaces = article.value.places.map((person) => person.list ?? [person]).flat();
        allPlaces.forEach(element => {element.etype = 'place'})

        let allEntities = allPersons.concat(allInstitutions, allPlaces)

        allEntities.sort(function(a, b) {return a.found_position - b.found_position;})

        let richText = ''
        let lastIndex = 0

        for (const entity of allEntities) {
            console.log(entity.found_position)
            richText += texthtml.substring(lastIndex, entity.found_position)
            if (entity.etype == 'person')
                richText += '<span style="color:red; font-weight:bold">'+entity.found_name+'</span>'
            else if (entity.etype == 'institution')
                richText += '<span style="color:blue; font-weight:bold">'+entity.found_name+'</span>'
            else if (entity.etype == 'place')
                richText += '<span style="color:purple; font-weight:bold">'+entity.found_name+'</span>'

            lastIndex = entity.found_position+entity.found_name.length
        }
        richText += texthtml.substring(lastIndex)

        return richText.split('\n').join('<br>')
    }
    const richText = ref('')

    // Handle update event for positivePeople
    const updatePositivePersons = (newValue) => {
        positivePersons.value = newValue
    };

    // Handle update event for positiveInstitutions
    const updatePositiveInstitutions = (newValue) => {
        positiveInstitutions.value = newValue;
    };

    // Handle update event for positivePlaces
    const updatePositivePlaces = (newValue) => {
        positivePlaces.value = newValue;
    };

    // Handle update event for positiveTags
    const updatePositiveOthers = (newValue) => {
        positiveOthers.value = newValue;
    };
</script>
