<template>
    <div class="p-4">
        <div class="max-w-sm rounded overflow-hidden shadow-lg mb-4 p-4">
            <p><a :href="article.url" class="font-bold text-xl mb-2">{{ article.title }}</a></p>
            <UBadge color="blue"> {{ article.url.split('/')[2] }} </UBadge>
            <p class="text-base">{{ article.description }}</p>
            <p class="text-base">{{ article.date }}</p>

            <UContainer class="flex justify-between px-0 sm:px-0 lg:px-0">
                <UButton color="red" @click="deleteArticle">Elutasít</UButton>
                <UButton @click="openModal">Tovább</UButton>
            </UContainer>
        </div>
        <UModal v-model="isOpen">
            <div class="p-4">
                <UInput class="my-2" v-model="article.title"/>
                <UInput class="my-2" v-model="article.url"/>
                <UTextarea class="my-2" v-model="article.description"/>
                <UTextarea class="my-2" v-model="article.text" rows="20"/>
                <SelectMenu class="my-2" :data="article.people" :positive-data="article.corrupt_people" />
                <SelectMenu class="my-2" :data="article.institutions" :positive-data="article.corrupt_institutions" />
                <SelectMenu class="my-2" :data="article.tags" :positive-data="article.tags" />
                <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                    <UButton color="gray" @click="closeModal">Mégse</UButton>
                    <UButton @click="submitArticle">Elfogad</UButton>
                </UContainer>
            </div>
        </UModal>
    </div>
</template>

<script setup lang="ts">
    async function postUrl(url, data) {
        return await $fetch(url)
        return await $fetch('https://corsproxy.io/?' + encodeURIComponent(url), data);
    }

    function openModal() {
        isOpen.value = true
    }
    function closeModal() {
        isOpen.value = false
    }
    async function deleteArticle() {
        await postUrl('http://kmonitordemo.duckdns.org/api/not_corruption', {
            method: 'POST',
            body: {'id': article.id}
        });
    }
    async function submitArticle() {
        await postUrl('http://kmonitordemo.duckdns.org/api/annote', {
            method: 'POST',
            body: {
                'id': article.id,
                'url': article.url,
                'title': article.title,
                'description': article.description,
                'text': article.text,
                'relations': article.relations,
                'people': article.people,
                'corrupt_people': article.corrupt_people,
                'institutions': article.institutions,
                'corrupt_institutions': article.corrupt_institutions,
                'tags': article.tags,
            }
        });
        isOpen.value = false
    }
    const isOpen = ref(false)

    const { article } = defineProps(['article']);
</script>
