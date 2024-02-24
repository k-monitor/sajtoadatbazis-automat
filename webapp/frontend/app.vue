<script setup lang="ts">
    var selectedDomain = ref('mind')

    const items = [{
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

    const allLabels = await getUrl('http://'+hostUrl+'/api/all_labels');

    const page = ref(1)
    let status = 'mixed'
    let response = await getUrl('http://'+hostUrl+'/api/articles?page='+(page.value)+'&status='+status+'&domain='+selectedDomain.value);
    var articles = response.articles
    let pages = response.pages;
    let itemsCount = ref(pages*10);

    let newUrl = '';
    let isOpen = ref(false);

    async function update() {
        const response = await getUrl('http://'+hostUrl+'/api/articles?page='+(page.value)+'&status='+status+'&domain='+selectedDomain.value);
        articles = response.articles
        pages = response.pages;
        itemsCount.value = pages*10;
    }

    function openNewUrl () {
        newUrl = ''
        isOpen.value = true
    }

    async function addUrl () {
        isOpen.value = false
        await $fetch('http://kmonitordemo.duckdns.org/api/add_url', {
            method: 'POST',
            body: {'url': newUrl},
        });
    }

    async function onChange (index) {
        const item = items[index]
        status = item.key
        console.log(status)
        await update()
    }

</script>

<template>
    <UContainer class="my-1 justify-between flex lg:px-0 px-4 sm:px-0 ml-1">
        <UButton class="mr-1" @click="openNewUrl">Új cikk</UButton>
        <UContainer class="my-1 flex lg:px-0 px-4 sm:px-0 ml-1">
            <p>Kiválasztott hírportál: &nbsp;</p>
            <UInputMenu class="w-48" v-model="selectedDomain" :options="allLabels['domains']" @change="update"  />
        </UContainer>
    </UContainer>
    <UModal v-model="isOpen">
        <div class="p-4">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrl" placeholder="https://telex.hu/..."/>
            <UButton @click="addUrl">Hozzáad</UButton>
        </div>
    </UModal>

    <UTabs :items="items" @change="onChange" class="w-full">
        <template #item="{ item }">
            <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article="article" :allLabels="allLabels" />
            <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="update" />
        </template>
    </UTabs>
</template>
