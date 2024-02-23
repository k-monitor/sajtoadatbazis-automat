<script setup lang="ts">
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

    const page = ref(1)
    let status = 'mixed'
    let response = await getUrl('http://'+hostUrl+'/api/articles?page='+(page.value)+'&status='+status);
    var articles = response.articles;
    let pages = response.pages;
    let itemsCount = ref(pages*10);

    let newUrl = '';
    let isOpen = ref(false);

    async function update() {
        const response = await getUrl('http://'+hostUrl+'/api/articles?page='+(page.value)+'&status='+status);
        articles = response.articles;
        pages = response.pages;
        itemsCount.value = pages;
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
    <UButton @click="openNewUrl">Új cikk</UButton>
    <UModal v-model="isOpen">
        <div class="p-4">
            <p>Új cikk</p>
            <UInput class="my-2" v-model="newUrl" placeholder="https://telex.hu/..."/>
            <UButton @click="addUrl">Hozzáad</UButton>
        </div>
    </UModal>

    <UTabs :items="items" @change="onChange" class="w-full">
        <template #item="{ item }">
            <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article=article />
            <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="update" />
        </template>
    </UTabs>
</template>
