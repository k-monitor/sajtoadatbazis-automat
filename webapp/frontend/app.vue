<script setup lang="ts">

    const items = [{
        label: 'Tab1',
        content: 'This is the content shown for Tab1'
    }, {
    label: 'Tab2',
        disabled: true,
        content: 'And, this is the content for Tab2'
    }, {
        label: 'Tab3',
        content: 'Finally, this is the content for Tab3'
    }]

    const page = ref(1)
    const response = await $fetch('/api/articles.json?page='+page.value);
    let articles = response.articles;
    let pages = response.pages;
    let itemsCount = ref(pages*10)

    async function update() {
        const response = await $fetch('/api/articles.json?page='+page.value);
        articles = response.articles;
        pages = response.pages;
        itemsCount = ref(pages*10)
    }
</script>

<template>
    <div class="">
        <h1>hello</h1>
        <Card class="flex justify-center" v-for="article in articles" :key="article.id" :article=article />
        <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @click="update" />
    </div>
</template>
