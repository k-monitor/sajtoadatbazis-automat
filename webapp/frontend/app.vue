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

    const page = ref(0)
    let response = await $fetch('http://'+hostUrl+'/api/articles?page='+page.value);
    let articles = response.articles;
    let pages = response.pages;
    let itemsCount = ref(pages*10)

    let newUrl = ''
    let isOpen = ref(false)

    async function update() {
        const response = await $fetch('http://'+hostUrl+'/api/articles?page='+page.value);
        articles = response.articles;
        pages = response.pages;
        itemsCount = ref(pages*10)
    }

    function openNewUrl () {
        newUrl = ''
        isOpen.value = true
    }

    async function addUrl () {
        isOpen.value = false
        await $fetch('http://kmonitordemo.duckdns.org/api/add_url', {
            method: 'POST',
            body: {'url': newUrl}
        });
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

    <UTabs :items="items" class="w-full">
        <template #item="{ item }">
            <Card class="flex justify-center" v-if="item.key === 'mixed'" v-for="article in articles" :key="article.id" :article=article />
            <UPagination class="p-4 justify-center" v-if="item.key === 'mixed'" v-model="page" :page-count="10" :total="itemsCount" @click="update" />
        </template>
    </UTabs>
</template>
