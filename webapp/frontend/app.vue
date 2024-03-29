<script setup lang="ts">
    const page = ref(1)
    const statusId = ref(0)
    const status = computed(() => statusItems[statusId.value].key)
    const selectedDomain = ref('mind')

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
            const {data, error} = await $fetch('http://kmonitordemo.duckdns.org/api/add_url', {
                method: 'POST',
                body: {'url': newUrl},
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
            <UInputMenu class="w-48" v-model="selectedDomain" :options="allLabels['domains']" @change="refresh"  />
        </UContainer>
    </UContainer>
    <UModal v-model="isOpen">
        <div class="p-4">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrl" placeholder="https://telex.hu/..."/>
            <UButton @click="addUrl">Hozzáad</UButton>
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
