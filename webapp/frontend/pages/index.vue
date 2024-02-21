<script setup>
    const articles = await $fetch(
    `/api/articles?page=1`
    );
</script>

<template>
    <div>
        <div class="container_main">
            <h1>hello</h1>
            <Card v-for="article in articles" :key="article.id" :article="article" />
        </div>
    </div>
</template>
