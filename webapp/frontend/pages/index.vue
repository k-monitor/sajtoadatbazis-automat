<script setup lang="ts">
definePageMeta({
  colorMode: "light",
});

import { sub, format } from "date-fns";
import { useAuthLazyFetch, useAuthFetch, $authFetch } from "~/auth_fetch";
import NewspaperSelectMenu from '~/components/NewspaperSelectMenu.vue';
import FindArticleByUrlModal from '~/components/FindArticleByUrlModal.vue';
import ArticleSearchResultModal from '~/components/ArticleSearchResultModal.vue';
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
let isAuthenticated = ref(true);
let selectedReasonId = ref(-1);
let isOpenFindByUrl = ref(false);
let isOpenSearchResult = ref(false);
let searchResultData = ref<{ mainArticle: any; groupedArticles: any[]; groupId: number | null } | null>(null);
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
let allLabels = ref<any | null>(null);
// let allLabels = (await useAuthFetch(baseUrl + "/api/domains")).data;
useAuthFetch(baseUrl + "/api/all_labels").then((response) => {
  allLabels.value = response.data.value;
  updateFromURL();
});
let keywordSynonyms: any = null;
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

function updateSelectedReason(newReason: { id: number }) {
  selectedReasonId.value = newReason.id;
  refresh();
}

function filterNewspaper(newspaper: { id: number; name: string }) {
  selectedDomains.value = [newspaper];
  updateURL();
}

function sendLoginError() {
  isAuthenticated.value = false;
}

function handleLoginSuccess() {
  isAuthenticated.value = true;
  refreshAll();
  document.location.reload();
}

function updateFromURL() {
  console.debug(query);
  if (query.statusId) {
    const statusQ = Array.isArray(query.statusId) ? query.statusId[0] : query.statusId;
    if (typeof statusQ === 'string') statusId.value = parseInt(statusQ);
  }
  if (query.selectedDomains) {
    const domainsQ = Array.isArray(query.selectedDomains) ? query.selectedDomains[0] : query.selectedDomains;
    const selectedDomainIds = typeof domainsQ === 'string'
      ? domainsQ.split(",").map((domain: string) => parseInt(domain))
      : [];
    console.debug(selectedDomainIds);
    selectedDomains.value = allDomains.value.filter(
      (domain) => selectedDomainIds.indexOf(domain.id) != -1
    );
    console.debug(selectedDomains.value);
  }
  if (query.page) {
    const pageQ = Array.isArray(query.page) ? query.page[0] : query.page;
    if (typeof pageQ === 'string') page.value = parseInt(pageQ);
  }
  if (query.reverseSort) {
    const rsQ = Array.isArray(query.reverseSort) ? query.reverseSort[0] : query.reverseSort;
    reverseSort.value = rsQ == "true" ? true : false;
  }
  if (query.q) {
    const qQ = Array.isArray(query.q) ? query.q[0] : query.q;
    if (typeof qQ === 'string') q.value = qQ;
  }
  if (query.dateFrom && query.dateTo) {
    const df = Array.isArray(query.dateFrom) ? query.dateFrom[0] : query.dateFrom;
    const dt = Array.isArray(query.dateTo) ? query.dateTo[0] : query.dateTo;
    if (typeof df === 'string' && typeof dt === 'string') {
      selected.value.start = new Date(df);
      selected.value.end = new Date(dt);
    }
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
  onResponse({ request, response, options }: any) {
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
  onResponse({ request, response, options }: any) {
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
let itemsCount = computed(() => (articleQuery.value == null ? 0 : (pages.value || 0) * 10));

const groupedArticles = computed(() => {
  if (!articles.value) return [] as Array<{ date: string; displayDate: string; articles: any[] }>;

  const list = articles.value as any[];
  // Separate articles with source=1 from other articles
  const priorityArticles = list.filter((article: any) => article.source === 1);
  const regularArticles = list.filter((article: any) => article.source !== 1);

  // Create groups for regular articles by date
  const groups: Record<string, any[]> = {};
  regularArticles.forEach((article: any) => {
    if (!article.date) return;
    const dateObj = new Date(article.date);
    const dateKey = dateObj.toISOString().split('T')[0];

    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(article);
  });

  // Sort date keys based on reverseSort flag
  const sortedDates = Object.keys(groups).sort((a, b) => {
    const ta = new Date(a).getTime();
    const tb = new Date(b).getTime();
    return reverseSort.value ? ta - tb : tb - ta;
  });

  // Sort articles within each date group based on reverseSort flag
  sortedDates.forEach((dateKey) => {
    groups[dateKey].sort((a: any, b: any) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return reverseSort.value ? dateA - dateB : dateB - dateA;
    });
  });

  // Convert to array of objects with date and articles
  let result = sortedDates.map((dateKey) => ({
    date: dateKey,
    articles: groups[dateKey],
    displayDate: new Date(dateKey).toLocaleDateString('hu-HU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }),
  }));

  // Always add priority articles at the beginning
  if (priorityArticles.length > 0) {
    priorityArticles.sort((a: any, b: any) => {
      const dateA = new Date(a.date).getTime();
      const dateB = new Date(b.date).getTime();
      return reverseSort.value ? dateA - dateB : dateB - dateA;
    });

    result.unshift({
      date: 'priority',
      articles: priorityArticles,
      displayDate: 'Kiemelt cikkek',
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

function updateSelectedDomains(newDomains: Array<{ id: number; name: string }>) {
  selectedDomains.value = newDomains;
  resetPageRefresh();
}

function updateSelectedDateRange(newRange: { start: Date; end: Date }) {
  selected.value = newRange;
  updateURL();
}

function updateReverseSort(newValue: boolean) {
  reverseSort.value = newValue;
  updateURL();
}

function openNewUrl() {
  isOpen.value = true;
}

function openFindByUrl() {
  isOpenFindByUrl.value = true;
}

async function handleFindArticleByUrl(url: string) {
  isOpenFindByUrl.value = false;
  
  try {
    const response = await $authFetch(baseUrl + "/api/article_by_url", {
      method: "POST",
      body: { url: url },
    });

    if (response.error) {
      isOpenError.value = true;
      errorText.value = response.error;
      errorTitle.value = "Hiba";
    } else {
      // Store the search result and open the result modal
      searchResultData.value = {
        mainArticle: response.main_article,
        groupedArticles: response.grouped_articles || [],
        groupId: response.group_id
      };
      isOpenSearchResult.value = true;
    }
  } catch (error: any) {
    console.error(error);
    isOpenError.value = true;
    errorText.value = error?.data?.error || "Hiba történt a keresés során!";
    errorTitle.value = "Hiba";
  }
}

// Per-article reasons are now selected on the cards; bulk action will apply them.

async function deleteArticles() {
  loadingDelete.value = true;
  async function applyAndClear(list: any[]) {
    for (const a of list) {
      if (!a) continue;
      if (a.pending_negative_reason != null) {
        await $authFetch(baseUrl + "/api/annote/negative", {
          method: "POST",
          body: { id: a.id, reason: a.pending_negative_reason },
        });
        a.pending_negative_reason = null;
      }
      if (Array.isArray(a.groupedArticles) && a.groupedArticles.length) {
        await applyAndClear(a.groupedArticles);
      }
    }
  }
  try {
    await applyAndClear(articles.value || []);
  } finally {
    loadingDelete.value = false;
    refreshAll();
  }
}

async function handleAddUrl(newUrl: string, selectedDomain: { id: number; name: string } | null) {
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
    errorText.value = String(error);
        errorTitle.value = "Hiba ";
      }
    }
  }
}
</script>

<template>
  <div>
    <!-- Show login form if not authenticated -->
    <LoginForm v-if="!isAuthenticated" @loginSuccess="handleLoginSuccess" />
    
    <!-- Show main content if authenticated -->
    <template v-else>
      <UContainer class="my-1 justify-between flex flex-wrap lg:px-0 px-4 sm:px-0 ml-1 max-w-full items-center">
        <PageTitle :baseUrl="baseUrl" />
        <a href="./stats"><Icon title="Statisztikák" name="mdi:chart-arc" size="30" style="color:rgb(34 197 94 / 1);"></Icon></a>
        <UContainer class="my-1 flex lg:px-0 px-2 sm:px-0 ml-auto mr-1 flex-wrap">
          <UButton class="mr-1 h-fit my-1" @click="openNewUrl">Új cikk</UButton>
          <UButton class="mr-1 h-fit my-1" color="blue" variant="outline" @click="openFindByUrl">
            <Icon name="mdi:magnify" class="mr-1" />
            Keresés URL-lel
          </UButton>
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
          <AnnoteMultiple :articles="articles" :loadingDelete="loadingDelete" @bulkDelete="deleteArticles" />
        </UContainer>
      </UContainer>

      <AddArticleModal :isOpen="isOpen" :domains="allLabels ? allLabels['domains'] : []" @update:isOpen="isOpen = $event"
        @add-url="handleAddUrl" />

      <FindArticleByUrlModal 
        :isOpen="isOpenFindByUrl" 
        @update:isOpen="isOpenFindByUrl = $event"
        @find-article="handleFindArticleByUrl" 
      />

      <ArticleSearchResultModal
        v-if="searchResultData"
        :isOpen="isOpenSearchResult"
        @update:isOpen="isOpenSearchResult = $event"
        :mainArticle="searchResultData.mainArticle"
        :groupedArticles="searchResultData.groupedArticles"
        :groupId="searchResultData.groupId"
        :allLabels="allLabels"
        :keywordSynonyms="keywordSynonyms"
        :allFiles="allFiles"
        :refresh="refreshAll"
        @filter-newspaper="filterNewspaper"
      />

      <UModal v-model="isOpenError" :prevent-close="true">
        <div class="p-4">
          <h1 class="font-bold">{{ errorTitle }}</h1>
          <p class="py-5">{{ errorText }}</p>
          <UButton @click="isOpenError = false">Bezárás</UButton>
        </div>
      </UModal>

      <UTabs :items="statusItems" v-model="statusId" @change="resetPageRefresh">
        <template #item="{ item }" v-if="!pending">
          <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount || 0" @change="refresh" />

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

          <UPagination class="p-4 justify-center" v-model="page" :page-count="10" :total="itemsCount || 0" @change="refresh" />
        </template>
        <template #item="{ item }" v-else>
          <UProgress animation="elastic" v-if="pending" />
        </template>
      </UTabs>
    </template>
  </div>
</template>

<style scoped>
.date-separator {
  width: 100%;
}
</style>
