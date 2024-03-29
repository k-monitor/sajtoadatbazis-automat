<script setup lang="ts">
    const page = ref(1)
    const statusId = ref(0)
    const status = computed(() => statusItems[statusId.value].key)
    const selectedDomainAdd = ref(null)

    const statusItems = [{
        label: 'Vegyes',
        key: 'mixed'
    }, {
        label: 'Elfogadott',
        key: 'positive'
    }, {
        label: 'Elutasított',
        key: 'negative'
    }]

    var hostUrl = 'kmonitordemo.duckdns.org'

    async function getUrl(url) {
        return await $fetch(url)
    }


    const { data: allLabels } = await useFetch('http://'+hostUrl+'/api/all_labels');
    let allDomains = [...allLabels.value.domains]
    if (allDomains[0].id != -1)
        allDomains.unshift({name: 'mind', id: -1})
    allDomains = ref(allDomains)
    const selectedDomain = ref(allDomains[0])

    const { pending, data, error, refresh } = await useLazyFetch('http://'+hostUrl+'/api/articles', {
        query: {
            page: page,
            status: status,
            domain: selectedDomain,
        },
    })

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
            console.log({
                    'url': newUrl,
                    'newspaper_name': selectedDomainAdd.value.name,
                    'newspaper_id': selectedDomainAdd.value.id,
                })
            const {data, error} = await $fetch('http://kmonitordemo.duckdns.org/api/add_url', {
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
    <UContainer class="my-1 justify-between flex lg:px-0 px-4 sm:px-0 ml-1">
        <UButton class="mr-1" @click="openNewUrl">Új cikk</UButton>
        <UContainer class="my-1 flex lg:px-0 px-4 sm:px-0 ml-1">
            <p>Kiválasztott hírportál: &nbsp;</p>
            <UInputMenu class="w-48" v-model="selectedDomain" option-attribute="name" value-attribute="id" :options="allDomains" @change="refresh"  />
        </UContainer>
    </UContainer>

    <UModal v-model="isOpen">
        <div class="p-4 h-80">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrl" placeholder="https://telex.hu/..."/>
            <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                <UInputMenu class="w-48" placeholder="válassz egy hírportált" v-model="selectedDomainAdd" option-attribute="name" :options="allLabels['domains']"  />
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

    <UTabs :items="statusItems" v-model="statusId" class="w-full">
        <template #item="{ item }" v-if="!pending">
            <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article="article" :allLabels="allLabels" />
            <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="refresh" />
        </template>
        <template #item="{ item }" v-else>
            <UProgress animation="elastic" v-if="pending" />
        </template>
    </UTabs>
</template>
