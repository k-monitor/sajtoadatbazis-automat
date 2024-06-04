<script setup lang="ts">
    let newUrl = '';
    let isOpen = ref(false);
    let isOpenError = ref(false);
    let errorText = ref('');
    let errorTitle = ref('');

    const page = ref(1)
    const statusId = ref(0)
    let q = ref('')
    let loadingDelete = ref(false)

    var baseUrl = 'https://autokmdb.deepdata.hu/autokmdb'
    // baseUrl = 'http://127.0.0.1:8000'

    const allLabels = useFetch(baseUrl+'/api/all_labels').data;
    let allDomains = computed(() => allLabels.value == null ? [] : [{name: 'mind', id: -1}].concat(allLabels.value?.domains))
    let allFiles = computed(() => allLabels.value == null ? [] : [{name: 'semmi', id: -1}].concat(allLabels.value?.files))
    const selectedDomain = ref(allDomains[0])

    const { data: articleCounts, refresh: refreshArticleCounts } = useLazyFetch(baseUrl+'/api/article_counts', {
        query: {
            domain: selectedDomain,
            q: q,
        },
        onResponse({ request, response, options }) {
            if (response.status >= 300) {
                isOpenError.value = true
                errorText.value = response._data.error
                errorTitle.value = 'Hiba ' + response.status
            }
        },
    });

    const statusItems = computed(() => [{
        label: `Ellenőrizendő (${articleCounts.value ? articleCounts.value['mixed'] : '...'})`,
        key: 'mixed'
    }, {
        label: `Elfogadott (${articleCounts.value ? articleCounts.value['positive'] : '...'})`,
        key: 'positive'
    }, {
        label: `Elutasított (${articleCounts.value ? articleCounts.value['negative'] : '...'})`,
        key: 'negative'
    }, {
        label: `Feldolgozás alatt (${articleCounts.value ? articleCounts.value['processing'] : '...'})`,
        key: 'processing'
    }, {
        label: `Mindegyik (${articleCounts.value ? articleCounts.value['all'] : '...'})`,
        key: 'all'
    }]);
    const status = computed(() => statusItems.value[statusId.value].key)

    const { pending, data: articleQuery, refresh } = useLazyFetch(baseUrl+'/api/articles', {
        query: {
            page: page,
            status: status,
            domain: selectedDomain,
            q: q,
        },
        onResponse({ request, response, options }) {
            if (response.status >= 300) {
                isOpenError.value = true
                errorText.value = response._data.error
                errorTitle.value = 'Hiba ' + response.status
            }
        },
    })

    let articles = computed(() => articleQuery.value?.articles);
    let pages = computed(() => articleQuery.value?.pages);
    let itemsCount = computed(() => articleQuery.value == null ? null : (pages.value*10));
    
    const selectedDomainAdd = ref(null)

    function resetPageRefresh() {
        page.value = 1
        refreshArticleCounts()
        refresh()
    }

    function openNewUrl () {
        newUrl = ''
        isOpen.value = true
    }

    async function deleteArticles() {
        console.log('hello')
        console.log(articles.value[0].selected)
        loadingDelete.value = true
        for (const article of articles.value) {
            if (article.selected) {
                await $fetch(baseUrl+'/api/annote/negative', {
                    method: 'POST',
                    body: {'id': article.id, 'reason': 0},
                });
            }
        }
        loadingDelete.value = false
        resetPageRefresh()
    }

    async function addUrl () {
        isOpen.value = false
        try {
            const {data} = await $fetch(baseUrl+'/api/add_url', {
                method: 'POST',
                body: {
                    'url': newUrl,
                    'newspaper_name': selectedDomainAdd.value.name,
                    'newspaper_id': selectedDomainAdd.value.id,
                },
                onResponse({ request, response, options }) {
                    if (response.status >= 300) {
                        isOpenError.value = true
                        errorText.value = response._data.error
                        errorTitle.value = 'Hiba ' + response.status
                    }
                },
            });
        } catch (error) {
            console.log(error)
            isOpenError.value = true
            errorText.value = error
            errorTitle.value = 'Hiba'
        }
    }
</script>

<template>
    <UContainer class="my-1 justify-between flex lg:px-0 px-4 sm:px-0 ml-1 max-w-full">
        <UButton class="mr-1" @click="openNewUrl">Új cikk</UButton>
        <div>
        <UContainer class="my-1 flex lg:px-0 px-4 sm:px-0 ml-1">
            <p>Kiválasztott hírportál: &nbsp;</p>
            <UInputMenu class="w-48" v-model="selectedDomain" option-attribute="name" value-attribute="id" :options="allDomains" @change="refresh">
                <template #option="{ option }">
                    <span><Icon v-if="option.has_rss" name="mdi:rss" color="orange"/> {{ option.name }}</span>
                </template>
            </UInputMenu>
            <UInput class="px-4" name="q" v-model="q" color="primary" variant="outline" placeholder="Keresés..." />
            <UButton v-if="articles && articles.some((v) => v.selected)" color="red" :loading="loadingDelete" @click="deleteArticles">{{"Kijelöltet elutasít ("+articles.filter((v)=> v.selected).length+")"}}</UButton>
        </UContainer>
    </div>
    </UContainer>

    <UModal v-model="isOpen">
        <div class="p-4 h-80">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrl" placeholder="https://telex.hu/..."/>
            <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                <UInputMenu class="w-48" placeholder="válassz egy hírportált" v-model="selectedDomainAdd" option-attribute="name" :options="allLabels['domains']">
                </UInputMenu>
                <UButton @click="addUrl">Hozzáad</UButton>
            </UContainer>
        </div>
    </UModal>

    <UModal v-model="isOpenError">
      <div class="p-4">
        <h2>{{ errorTitle }}</h2>
        <p>{{ errorText }}</p>
        <UButton @click="isOpenError = false">Bezárás</UButton>
      </div>
    </UModal>


    <UTabs :items="statusItems" v-model="statusId" @change="resetPageRefresh">
        <template #item="{ item }" v-if="!pending">
            <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article="article" :allLabels="allLabels" :allFiles="allFiles" :refresh="refresh" />
            <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="refresh" />
        </template>
        <template #item="{ item }" v-else>
            <UProgress animation="elastic" v-if="pending" />
        </template>
    </UTabs>
</template>
