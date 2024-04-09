<script setup lang="ts">
    const page = ref(1)
    const statusId = ref(0)
    const status = computed(() => statusItems[statusId.value].key)
    const selectedDomainAdd = ref(null)

    const statusItems = [{
        label: 'Ellenőrizendő',
        key: 'mixed'
    }, {
        label: 'Elfogadott',
        key: 'positive'
    }, {
        label: 'Elutasított',
        key: 'negative'
    }, {
        label: 'Feldolgozás alatt',
        key: 'processing'
    }]

    var baseUrl = 'https://adatbazis.k-monitor.hu/autokmdb'

    async function getUrl(url) {
        return await $fetch(url)
    }


    const { data: allLabels } = await useFetch(baseUrl+'/api/all_labels');
    let allDomains = [...allLabels.value.domains]
    if (allDomains[0].id != -1)
        allDomains.unshift({name: 'mind', id: -1})
    allDomains = ref(allDomains)
    const selectedDomain = ref(allDomains[0])
    let q = ref('')

    const { pending, data, error, refresh } = await useLazyFetch(baseUrl+'/api/articles', {
        query: {
            page: page,
            status: status,
            domain: selectedDomain,
            q: q,
        },
    })

    function resetPageRefresh() {
        page.value = 1
        refresh()
    }

    let articles = computed(() => data.value.articles);
    let pages = computed(() => data.value.pages);
    let itemsCount = computed(() => pages.value*10);

    let newUrl = '';
    let isOpen = ref(false);
    let isOpenError = ref(false);
    let errorText = ref('');
    let errorTitle = ref('');

    function openNewUrl () {
        newUrl = ''
        isOpen.value = true
    }

    async function addUrl () {
        isOpen.value = false
        try {
            const {data, error} = await $fetch(baseUrl+'/api/add_url', {
                method: 'POST',
                body: {
                    'url': newUrl,
                    'newspaper_name': selectedDomainAdd.value.name,
                    'newspaper_id': selectedDomainAdd.value.id,
                },
            });
            if (error) {
                console.log(error)
                isOpenError.value = true
                errorText.value = data.error
                errorTitle.value = 'Hiba'
            }
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
            <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article="article" :allLabels="allLabels" :refresh="refresh" />
            <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="refresh" />
        </template>
        <template #item="{ item }" v-else>
            <UProgress animation="elastic" v-if="pending" />
        </template>
    </UTabs>
</template>
