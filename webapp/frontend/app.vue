<script setup lang="ts">
definePageMeta({
  colorMode: "light",
});

import { sub, format, isSameDay, type Duration } from "date-fns";

const route = useRoute();
const router = useRouter();

const ranges = [
  { label: "Last 7 days", duration: { days: 7 } },
  { label: "Last 14 days", duration: { days: 14 } },
  { label: "Last 30 days", duration: { days: 30 } },
  { label: "Last 3 months", duration: { months: 3 } },
  { label: "Last 6 months", duration: { months: 6 } },
  { label: "Last year", duration: { years: 1 } },
  { label: "2 years", duration: { years: 2 } },
  { label: "3 years", duration: { years: 3 } },
];

const selected = ref({ start: sub(new Date(), { days: 14 }), end: new Date() });
function selectRange(duration: Duration) {
  selected.value = { start: sub(new Date(), duration), end: new Date() };
}

function isRangeSelected(duration: Duration) {
  return (
    isSameDay(selected.value.start, sub(new Date(), duration)) &&
    isSameDay(selected.value.end, new Date())
  );
}
let newUrl = "";
let isOpen = ref(false);
let isOpenError = ref(false);
let errorText = ref("");
let errorTitle = ref("");
let reverseSort = ref(false);
let loginError = ref(false);

const page = ref(1);
const statusId = ref(0);
let q = ref("");
let loadingDelete = ref(false);

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;

const allLabels = useFetch(baseUrl + "/api/all_labels").data;
const keywordSynonyms = useFetch(baseUrl + "/api/keyword_synonyms").data;

let allFiles = computed(() =>
  allLabels.value == null ? [] : allLabels.value?.files
);
let allDomains = computed(() =>
  allLabels.value == null
    ? []
    : [{ name: "mind", id: -1 }].concat(allLabels.value?.domains)
);
const selectedDomains = ref([{ name: "mind", id: -1 }]);

watch(
  selectedDomains,
  (newVal) => {
    const mindIndex = newVal.findIndex((domain) => domain.id === -1);
    const hasOtherSelections = newVal.some((domain) => domain.id !== -1);

    if (hasOtherSelections) {
      if (mindIndex === 0)
        selectedDomains.value = newVal.filter((domain) => domain.id !== -1);
      else if (mindIndex !== -1)
        selectedDomains.value = newVal.filter((domain) => domain.id == -1);
    }

    if (!hasOtherSelections && mindIndex === -1) {
      selectedDomains.value = [{ name: "mind", id: -1 }];
    }
  },
  { immediate: true }
);

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

function updateFromURL() {
  if (route.query.statusId) {
    statusId.value = parseInt(route.query.statusId);
  }
  if (route.query.selectedDomains) {
    const selectedDomainIds = route.query.selectedDomains
      .split(",")
      .map((domain: string) => parseInt(domain));
    selectedDomains.value = allDomains.value.filter(
      (domain) => selectedDomainIds.indexOf(domain.id) != -1
    );
  }
  if (route.query.page) {
    page.value = parseInt(route.query.page);
  }
  if (route.query.reverseSort) {
    reverseSort.value = route.query.reverseSort == "true" ? true : false;
  }
  if (route.query.q) {
    q.value = route.query.q;
  }
}

const { data: articleCounts, refresh: refreshArticleCounts } = useLazyFetch(
  baseUrl + "/api/article_counts",
  {
    method: "POST",
    body: {
      domain: selectedDomains,
      from: from,
      to: to,
      q: q,
    },
    onResponse({ request, response, options }) {
      if (response.status == 401) {
        loginError.value = true;
        isOpenError.value = true;
        errorText.value = 'Kérlek, jelentkezz be a K-Monitor Adatbázis admin felületén, majd töltsd újra ezt a lapot!';
        errorTitle.value = "Hiba";
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
    label: `Ellenőrizendő (${
      articleCounts.value ? articleCounts.value["mixed"] : "..."
    })`,
    key: "mixed",
  },
  {
    label: `Elfogadott (${
      articleCounts.value ? articleCounts.value["positive"] : "..."
    })`,
    key: "positive",
  },
  {
    label: `Elutasított (${
      articleCounts.value ? articleCounts.value["negative"] : "..."
    })`,
    key: "negative",
  },
  {
    label: `Feldolgozás alatt (${
      articleCounts.value ? articleCounts.value["processing"] : "..."
    })`,
    key: "processing",
  },
  {
    label: `Mindegyik (${
      articleCounts.value ? articleCounts.value["all"] : "..."
    })`,
    key: "all",
  },
]);

updateFromURL();
// updateURL();

watch(statusId, updateURL);
watch(q, updateURL);
watch(allDomains, updateFromURL);

const {
  pending,
  data: articleQuery,
  refresh: refreshArticles,
} = useLazyFetch(baseUrl + "/api/articles", {
  method: "POST",
  body: {
    page: page,
    status: status,
    domain: selectedDomains,
    from: from,
    to: to,
    reverse: reverseSort,
    q: q,
  },
  onResponse({ request, response, options }) {
    if (response.status == 401) {
      loginError.value = true;
      isOpenError.value = true;
      errorText.value = 'Kérlek, jelentkezz be a K-Monitor Adatbázis admin felületén, majd töltsd újra ezt a lapot!';
      errorTitle.value = "Hiba";
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

function refresh() {
  updateURL();
  refreshArticles();
}

const selectedDomainAdd = ref(null);

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

function filterNewspaper(selectedNewspaper) {
  selectedDomains.value = [selectedNewspaper]
}

function openNewUrl() {
  newUrl = "";
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
      await $fetch(baseUrl + "/api/annote/negative", {
        method: "POST",
        body: { id: article.id, reason: reason },
      });
    }
  }
  loadingDelete.value = false;
  resetPageRefresh();
}

async function addUrl() {
  isOpen.value = false;
  try {
    await $fetch(baseUrl + "/api/add_url", {
      method: "POST",
      body: {
        url: newUrl,
        newspaper_name: selectedDomainAdd.value.name,
        newspaper_id: selectedDomainAdd.value.id,
      },
      onResponse({ request, response, options }) {},
      onResponseError({ request, response, options }) {
        console.log("1");
        isOpenError.value = true;
        errorText.value = response._data.error;
        errorTitle.value = "Hiba " + response.status;
      },
    });
  } catch (error) {
    console.log("3");
    console.log(error);
    if (!isOpenError.value) {
      isOpenError.value = true;
      errorText.value = error;
      errorTitle.value = "Hiba ";
    }
  }
}
</script>

<template>
  <div>
    <UContainer
      class="my-1 justify-between flex lg:px-0 px-4 sm:px-0 ml-1 max-w-full"
    >
      <UContainer class="my-1 flex lg:px-0 px-2 sm:px-0 ml-auto mr-1 flex-wrap">
        <UButton class="mr-1 h-fit my-1" @click="openNewUrl">Új cikk</UButton>
        <div class="flex my-auto px-1 my-1">
          <p>Kiválasztott hírportál: &nbsp;</p>
          <USelectMenu
            searchable
            :search-attributes="['name']"
            searchable-placeholder="Keresés..."
            clear-search-on-close
            multiple
            class="w-48"
            v-model="selectedDomains"
            by="id"
            :options="allDomains"
            @change="refresh"
          >
            <template #option="{ option }">
              <span
                ><Icon v-if="option.has_rss" name="mdi:rss" class="text-yellow-500" />
                {{ option.name }}</span
              >
            </template>
            <template #empty> betöltés... </template>
            <template #label>
              <span>{{
                selectedDomains
                  .map((item) => ("name" in item ? item.name : "mind"))
                  .join(", ")
              }}</span>
            </template>
          </USelectMenu>
        </div>
        <UButton
          class="h-fit my-1"
          :icon="
            reverseSort ? 'i-heroicons-arrow-up' : 'i-heroicons-arrow-down'
          "
          size="sm"
          color="primary"
          square
          variant="solid"
          @click="
            () => {
              reverseSort = !reverseSort;
              refresh();
            }
          "
        />
        <UPopover class="px-1" :popper="{ placement: 'bottom-start' }">
          <UButton icon="i-heroicons-calendar-days-20-solid" class=" my-1">
            {{ format(selected.start, "yyyy. MM. dd.") }} -
            {{ format(selected.end, "yyyy. MM. dd.") }}
          </UButton>

          <template #panel="{ close }">
            <div
              class="flex items-center sm:divide-x divide-gray-200 dark:divide-gray-800"
            >
              <div class="hidden sm:flex flex-col py-4">
                <UButton
                  v-for="(range, index) in ranges"
                  :key="index"
                  :label="range.label"
                  color="gray"
                  variant="ghost"
                  class="rounded-none px-6"
                  :class="[
                    isRangeSelected(range.duration)
                      ? 'bg-gray-100 dark:bg-gray-800'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
                  ]"
                  truncate
                  @click="selectRange(range.duration)"
                />
              </div>

              <DatePicker
                v-model="selected"
                is-required
                @close="
                  () => {
                    close();
                    refresh();
                  }
                "
              />
            </div>
          </template>
        </UPopover>

        <UInput
          class="px-1 my-1"
          name="q"
          v-model="q"
          color="primary"
          variant="outline"
          placeholder="Keresés..."
        />
        <UDropdown class="left-5 bottom-5 fixed z-10 my-1" label="Elutasít" :items="items"
          :popper="{ placement: 'bottom-end' }" v-if="articles && articles.some((v) => v.selected)">
          <UButton
            color="red"
            :label="'Kijelöltet elutasít (' + articles.filter((v) => v.selected).length + ')'"
            trailing-icon="i-heroicons-chevron-down-20-solid"
            :loading="loadingDelete"
            />
          <template #item="{ item }">
            <span class="">{{ item.label }}</span>
          </template>
        </UDropdown>
      </UContainer>
    </UContainer>

    <UModal v-model="isOpen">
      <div class="p-4">
        <p>Új cikk</p>
        <UInput
          class="my-2"
          v-model="newUrl"
          placeholder="https://telex.hu/..."
        />
        <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
          <UInputMenu
            class="w-48"
            placeholder="válassz egy hírportált"
            v-model="selectedDomainAdd"
            option-attribute="name"
            :options="allLabels['domains']"
          >
          </UInputMenu>
          <UButton @click="addUrl">Hozzáad</UButton>
        </UContainer>
      </div>
    </UModal>

    <UModal v-model="isOpenError" :prevent-close="true">
      <div class="p-4">
        <h1 class="font-bold">{{ errorTitle }}</h1>
        <p class="py-5">{{ errorText }}</p>
        <p v-if="loginError"><a href="https://autokmdb.deepdata.hu/admin.php" target="_blank" class="text-blue-700">admin felület</a></p>
        <UButton v-else @click="isOpenError = false">Bezárás</UButton>
      </div>
    </UModal>

    <UTabs :items="statusItems" v-model="statusId" @change="resetPageRefresh">
      <template #item="{ item }" v-if="!pending">
        <UPagination
          class="p-4 justify-center"
          v-model="page"
          :page-count="10"
          :total="itemsCount"
          @change="refresh"
        />
        <Card
          class="flex justify-center"
          v-for="article in articles"
          :key="article.id"
          :article="article"
          :allLabels="allLabels"
          :keywordSynonyms="keywordSynonyms"
          :allFiles="allFiles"
          :refresh="refreshAll"
          @update:filter_newspaper="filterNewspaper"
        />
        <UPagination
          class="p-4 justify-center"
          v-model="page"
          :page-count="10"
          :total="itemsCount"
          @change="refresh"
        />
      </template>
      <template #item="{ item }" v-else>
        <UProgress animation="elastic" v-if="pending" />
      </template>
    </UTabs>
  </div>
</template>
