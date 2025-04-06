<script setup lang="ts">
definePageMeta({
  colorMode: "light",
});

import { sub, format } from "date-fns";
import { useAuthLazyFetch, useAuthFetch, $authFetch } from "~/auth_fetch";
import NewspaperSelectMenu from '~/components/NewspaperSelectMenu.vue';
import { useRoute, useRouter } from 'vue-router'; // Ensure vue-router is imported

const route = useRoute();
const router = useRouter();

const ranges = [
  { label: "Elmúlt 1 nap", duration: { days: 1 } },
  { label: "Elmúlt 2 nap", duration: { days: 2 } },
  { label: "Elmúlt 7 nap", duration: { days: 7 } },
  { label: "Elmúlt 2 hét", duration: { days: 14 } },
  { label: "Elmúlt 1 hónap", duration: { days: 30 } },
  { label: "Elmúlt 3 hónap", duration: { months: 3 } },
  { label: "Elmúlt 6 hónap", duration: { months: 6 } },
  { label: "Elmúlt 1 év", duration: { years: 1 } },
  { label: "Elmúlt 3 év", duration: { years: 3 } },
];
const query = route.query;

const selected = ref({ start: sub(new Date(), { days: 14 }), end: new Date() });
let isOpen = ref(false);
let isOpenError = ref(false);
let errorText = ref("");
let errorTitle = ref("");
let reverseSort = ref(false);
let loginError = ref(false);
let selectedReasonId = ref(-1);
const reasons = [
  { name: "Bármilyen ok", id: -1 },
  { name: "Átvett", id: 2 },
  { name: "Letöltési hiba", id: 3 },
  { name: "Feldolgozási hiba", id: 4 },
];

const page = ref(1);
const statusId = ref(0);
let q = ref("");
let loadingDelete = ref(false);

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;
let allLabels = ref(null);
// let allLabels = (await useAuthFetch(baseUrl + "/api/domains")).data;
useAuthFetch(baseUrl + "/api/all_labels").then((response) => {
  allLabels.value = response.data.value;
  updateFromURL();
});
let keywordSynonyms = null;
useAuthFetch(baseUrl + "/api/keyword_synonyms").then((response) => {
  keywordSynonyms = response.data;
});

let allFiles = computed(() =>
  allLabels.value == null ? [] : allLabels.value?.files
);
let allDomains = computed(() =>
  allLabels.value == null
    ? []
    : [{ name: "mind", id: -1 }].concat(allLabels.value?.domains)
);
const selectedDomains = ref([{ name: "mind", id: -1 }]);

const status = computed(() => statusItems.value[statusId.value].key);
const from = computed(() => format(selected.value.start, "yyyy-MM-dd"));
const to = computed(() => format(selected.value.end, "yyyy-MM-dd"));

function updateURL() {
  router.push({
    query: {
      statusId: statusId.value,
      selectedDomains: selectedDomains.value
        .map((domain) => domain.id)
        .join(","),
      page: page.value,
      reverseSort: reverseSort.value ? "true" : "false",
      q: q.value,
    },
  });
}

function updateSelectedReason(newReason) {
  selectedReasonId.value = newReason.id;
  refresh();
}

function filterNewspaper(newspaper) {
  selectedDomains.value = [newspaper];
  updateURL();
}

function sendLoginError() {
  loginError.value = true;
  isOpenError.value = true;
  errorText.value = 'Kérlek, jelentkezz be a K-Monitor Adatbázis admin felületén, majd töltsd újra ezt a lapot!';
  errorTitle.value = "Hiba";
}

function updateFromURL() {
  console.debug(query);
  if (query.statusId) {
    statusId.value = parseInt(query.statusId);
  }
  if (query.selectedDomains) {
    const selectedDomainIds = query.selectedDomains
      .split(",")
      .map((domain: string) => parseInt(domain));
    console.debug(selectedDomainIds);
    selectedDomains.value = allDomains.value.filter(
      (domain) => selectedDomainIds.indexOf(domain.id) != -1
    );
    console.debug(selectedDomains.value);
  }
  if (query.page) {
    page.value = parseInt(query.page);
  }
  if (query.reverseSort) {
    reverseSort.value = query.reverseSort == "true" ? true : false;
  }
  if (query.q) {
    q.value = query.q;
  }
}

const { data: articleCounts, refresh: refreshArticleCounts } = useAuthLazyFetch(
  baseUrl + "/api/article_counts",
  {
    method: "POST",
    body: {
      domain: selectedDomains,
      from: from,
      to: to,
      q: q,
      skip_reason: selectedReasonId,
    },
    onResponse({ request, response, options }) {
      if (response.status == 401) {
        sendLoginError();
      } else if (response.status >= 300) {
        loginError.value = false;
        isOpenError.value = true;
        errorText.value = response._data.error;
        errorTitle.value = "Hiba " + response.status;
      }
    },
  }
);

const statusItems = computed(() => [
  {
    label: `Ellenőrizendő (${articleCounts.value ? articleCounts.value["mixed"] : "..."
      })`,
    key: "mixed",
  },
  {
    label: `Elfogadott (${articleCounts.value ? articleCounts.value["positive"] : "..."
      })`,
    key: "positive",
  },
  {
    label: `Elutasított (${articleCounts.value ? articleCounts.value["negative"] : "..."
      })`,
    key: "negative",
  },
  {
    label: `Feldolgozás alatt (${articleCounts.value ? articleCounts.value["processing"] : "..."
      })`,
    key: "processing",
  },
  {
    label: `Mindegyik (${articleCounts.value ? articleCounts.value["all"] : "..."
      })`,
    key: "all",
  },
]);

updateFromURL();
// updateURL();

watch(statusId, updateURL);
watch(q, updateURL);
watch(allDomains, updateURL);

const {
  pending,
  data: articleQuery,
  refresh: refreshArticles,
} = useAuthLazyFetch(baseUrl + "/api/articles", {
  method: "POST",
  body: {
    page: page,
    status: status,
    domain: selectedDomains,
    from: from,
    to: to,
    reverse: reverseSort,
    q: q,
    skip_reason: selectedReasonId,
  },
  onResponse({ request, response, options }) {
    if (response.status == 401) {
      sendLoginError();
    } else if (response.status >= 300) {
      loginError.value = false;
      isOpenError.value = true;
      errorText.value = response._data.error;
      errorTitle.value = "Hiba " + response.status;
    }
  },
});

let articles = computed(() => articleQuery.value?.articles);
let pages = computed(() => articleQuery.value?.pages);
let itemsCount = computed(() =>
  articleQuery.value == null ? null : pages.value * 10
);

const groupedArticles = computed(() => {
  if (!articles.value) return [];
  
  // Separate articles with source=1 from other articles
  const priorityArticles = articles.value.filter(article => article.source === 1);
  const regularArticles = articles.value.filter(article => article.source !== 1);
  
  // Create groups for regular articles by date
  const groups = {};
  regularArticles.forEach(article => {
    // Parse the date from the format "Fri, 07 Mar 2025 10:09:27 GMT"
    if (!article.date) return;
    
    const dateObj = new Date(article.date);
    // Format as YYYY-MM-DD for grouping
    const dateKey = dateObj.toISOString().split('T')[0];

    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(article);
  });
  
  // Sort date keys based on reverseSort flag
  const sortedDates = Object.keys(groups).sort((a, b) => {
    // If reverseSort is true, oldest first; if false, newest first
    return reverseSort.value 
      ? new Date(a) - new Date(b) 
      : new Date(b) - new Date(a);
  });
  
  // Sort articles within each date group based on reverseSort flag
  sortedDates.forEach(dateKey => {
    groups[dateKey].sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return reverseSort.value 
        ? dateA - dateB 
        : dateB - dateA;
    });
  });
  
  // Convert to array of objects with date and articles
  let result = sortedDates.map(dateKey => ({
    date: dateKey,
    articles: groups[dateKey],
    // Format the date for display
    displayDate: new Date(dateKey).toLocaleDateString('hu-HU', {
      year: 'numeric',
      month: 'long', 
      day: 'numeric'
    })
  }));
  
  // Always add priority articles at the beginning
  if (priorityArticles.length > 0) {
    priorityArticles.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return reverseSort.value 
        ? dateA - dateB 
        : dateB - dateA;
    });
    
    result.unshift({
      date: 'priority',
      articles: priorityArticles,
      displayDate: 'Kiemelt cikkek'
    });
  }
  
  return result;
});

function refresh() {
  updateURL();
  refreshArticles();
}

function resetPageRefresh() {
  page.value = 1;
  updateURL();
  refreshArticleCounts();
  refreshArticles();
}

function refreshAll() {
  refreshArticleCounts();
  refresh();
}

function updateSelectedDomains(newDomains) {
  selectedDomains.value = newDomains;
  resetPageRefresh();
}

function updateSelectedDateRange(newRange) {
  selected.value = newRange;
  updateURL();
}

function updateReverseSort(newValue) {
  reverseSort.value = newValue;
  updateURL();
}

function openNewUrl() {
  isOpen.value = true;
}

const items = [
  [
    {
      label: "Nem releváns",
      slot: "item",
      click: async () => deleteArticles(0),
    },
    {
      label: "Átvett",
      slot: "item",
      click: async () => deleteArticles(1),
    },
    {
      label: "Már szerepel",
      slot: "item",
      click: async () => deleteArticles(3),
    },
    {
      label: "Külföldi",
      slot: "item",
      click: async () => deleteArticles(2),
    },
    {
      label: "Egyéb",
      slot: "item",
      click: async () => deleteArticles(100),
    },
  ],
];

async function deleteArticles(reason) {
  console.debug(articles.value[0].selected);
  console.debug(reason);
  loadingDelete.value = true;
  for (const article of articles.value) {
    if (article.selected) {
      await $authFetch(baseUrl + "/api/annote/negative", {
        method: "POST",
        body: { id: article.id, reason: reason },
      });
    }
  }
  loadingDelete.value = false;
  // resetPageRefresh();
  refreshAll();
}

async function handleAddUrl(newUrl, selectedDomain) {
  isOpen.value = false;
  if (selectedDomain === null) {
    isOpenError.value = true;
    errorText.value = "Válaszd ki a listából a cikkhez tartozó hírportált!";
    errorTitle.value = "Hiba ";
  } else if (newUrl === '') {
    isOpenError.value = true;
    errorText.value = "Adj meg url-t is!";
    errorTitle.value = "Hiba ";
  } else {
    try {
      useAuthFetch(baseUrl + "/api/add_url", {
        method: "POST",
        body: {
          url: newUrl,
          newspaper_name: selectedDomain.name,
          newspaper_id: selectedDomain.id,
        },
      }).then((response) => {
        if (response.status.value == "error") {
          isOpenError.value = true;
          errorText.value = response.error.value?.data?.error;
          errorTitle.value = "Hiba";
        }
      });
    } catch (error) {
      console.error(error);
      if (!isOpenError.value) {
        isOpenError.value = true;
        errorText.value = error;
        errorTitle.value = "Hiba ";
      }
    }
  }
}
</script>

<template>
  <div>
    <UContainer class="my-1 justify-between flex flex-wrap lg:px-0 px-4 sm:px-0 ml-1 max-w-full items-center">
      <PageTitle :baseUrl="baseUrl" />
      <a href="./stats"><Icon title="Statisztikák" name="mdi:chart-arc" size="30" style="color:rgb(34 197 94 / 1);"></Icon></a>
      <UContainer class="my-1 flex lg:px-0 px-2 sm:px-0 ml-auto mr-1 flex-wrap">
        <UButton class="mr-1 h-fit my-1" @click="openNewUrl">Új cikk</UButton>
        <div class="flex my-auto px-1 my-1">
          <NewspaperSelectMenu :allDomains="allDomains" :selectedDomains="selectedDomains"
            @update:selectedDomains="updateSelectedDomains" @refresh="refresh" />
        </div>

        <ReverseSortButton :reverseSort="reverseSort" @update:reverseSort="updateReverseSort" @refresh="refresh" />

        <DateRangeSelector :selected="selected" :ranges="ranges" @update:selected="updateSelectedDateRange"
          @refresh="refresh" />

        <SkipReasonSelectMenu v-if="statusId == 4" :reasons="reasons" @update:selectedReason="updateSelectedReason"
          @refresh="refresh" />

        <UInput class="px-1 my-1" name="q" v-model="q" color="primary" variant="outline" placeholder="Keresés..." />
        <AnnoteMultiple :articles="articles" :items="items" :loadingDelete="loadingDelete" />
      </UContainer>
    </UContainer>

    <AddArticleModal :isOpen="isOpen" :domains="allLabels ? allLabels['domains'] : []" @update:isOpen="isOpen = $event"
      @add-url="handleAddUrl" />

    <UModal v-model="isOpenError" :prevent-close="true">
      <div class="p-4">
        <h1 class="font-bold">{{ errorTitle }}</h1>
        <p class="py-5">{{ errorText }}</p>
        <p v-if="loginError"><a :href="config.public.adminUrl" target="_blank" class="text-blue-700">admin felület</a>
        </p>
        <UButton v-else @click="isOpenError = false">Bezárás</UButton>
      </div>
    </UModal>

    <UTabs :items="statusItems" v-model="statusId" @change="resetPageRefresh">
      <template #item="{ item }" v-if="!pending">
        <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @change="refresh" />

        <template v-for="(group, index) in groupedArticles" :key="group.date">
          <!-- Date separator -->
          <div class="date-separator my-4 flex items-center">
            <div class="h-px bg-gray-300 flex-grow mr-4"></div>
            <div class="text-lg font-semibold text-gray-700">{{ group.displayDate }}</div>
            <div class="h-px bg-gray-300 flex-grow ml-4"></div>
          </div>

          <div class="flex flex-col items-center">
            <Card 
              v-for="article in group.articles" 
              :key="article.id" 
              :article="article" 
              :allLabels="allLabels" 
              :keywordSynonyms="keywordSynonyms" 
              :allFiles="allFiles" 
              :refresh="refreshAll"
              :is_small="false"
              @update:filter_newspaper="filterNewspaper" 
              class="w-full max-w-2xl"
            />
          </div>
        </template>

        <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount" @change="refresh" />
      </template>
      <template #item="{ item }" v-else>
        <UProgress animation="elastic" v-if="pending" />
      </template>
    </UTabs>
  </div>
</template>

<style scoped>
.date-separator {
  width: 100%;
}
</style>
