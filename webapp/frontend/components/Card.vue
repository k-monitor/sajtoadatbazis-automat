<template>
    <div class="p-4">
        <div class="max-w-sm rounded overflow-hidden shadow-lg mb-4 p-4">
            <p>
                <a :href="article.url" class="font-bold text-xl mb-2">{{ article.title }}</a>
                <UBadge class="m-1" color="gray">
                <Icon v-if="!article.is_annoted" name="mdi:question-mark" color="gray" />
                <Icon v-if="article.is_annoted && !article.is_annoted_corruption" name="mdi:trash" color="red" />
                <Icon v-if="article.is_annoted && article.is_annoted_corruption" name="mdi:tick" color="green" />
                </UBadge>
            </p>
            <UBadge class="m-1" color="blue"> {{ article.url.split('/')[2] }} </UBadge>
            <p class="text-base">{{ article.description }}</p>
            <p class="text-base">{{ article.date }}</p>

            <UContainer class="flex justify-between px-0 sm:px-0 lg:px-0">
                <UButton v-if="!article.is_annoted || article.is_annoted_corruption" color="red" @click="deleteArticle">Elutasít</UButton>
                <UButton v-if="!article.is_annoted || !article.is_annoted_corruption" @click="openModal" class="ml-auto">Tovább</UButton>
            </UContainer>
        </div>
        <UModal v-model="isOpen">
            <div class="p-4">
                <p>Cím:</p>
                <UInput class="my-2" v-model="article.title"/>
                <p>URL:</p>
                <UInput class="my-2" v-model="article.url"/>
                <p>Leírás:</p>
                <UTextarea class="my-2" v-model="article.description"/>
                <p>Szöveg:</p>
                <UTextarea class="my-2" v-model="article.text" rows="20"/>
                <SelectMenu class="my-2" :data="article.people" type="személy" :positive-data="article.corrupt_people" :labels="allLabels['person']" />
                <SelectMenu class="my-2" :data="article.institutions" type="intézmény" :positive-data="article.corrupt_institutions" :labels="allLabels['institution']" />
                <SelectMenu class="my-2" :data="article.places" type="helyszín" :positive-data="article.corrupt_places" :labels="allLabels['place']" />
                <SelectMenu class="my-2" :data="article.tags" type="egyéb" :positive-data="article.tags" :labels="allLabels['other']" />
                <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
                    <UButton color="gray" @click="closeModal">Mégse</UButton>
                    <UButton @click="submitArticle">Elfogad</UButton>
                </UContainer>
            </div>
        </UModal>
    </div>
</template>

<script setup lang="ts">
    var hostUrl = 'kmonitordemo.duckdns.org'
    //hostUrl = 'localhost:3000'

    async function postUrl(url, data) {
        return await $fetch(url, data)
    }

    function openModal() {
        isOpen.value = true
    }
    function closeModal() {
        isOpen.value = false
    }
    async function deleteArticle() {
        await postUrl('http://'+hostUrl+'/api/not_corruption', {
            method: 'POST',
            body: {'id': article.id}
        });
    }
    async function submitArticle() {
        await postUrl('http://'+hostUrl+'/api/annote', {
            method: 'POST',
            body: {
                'id': article.id,
                'url': article.url,
                'title': article.title,
                'description': article.description,
                'text': article.text,
                'people': article.people,
                'corrupt_people': article.corrupt_people,
                'institutions': article.institutions,
                'corrupt_institutions': article.corrupt_institutions,
                'places': article.places,
                'corrupt_places': article.corrupt_places,
                'tags': article.tags,
            }
        });
        isOpen.value = false
    }
    const isOpen = ref(false)

    const { article, allLabels } = defineProps(['article', 'allLabels']);
</script>
