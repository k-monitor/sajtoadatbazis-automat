<script setup lang="ts">
definePageMeta({
  colorMode: "light",
});

import { sub, format, isSameDay, type Duration } from "date-fns";

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

const page = ref(1);
const statusId = ref(0);
let q = ref("");
let loadingDelete = ref(false);

var baseUrl = "https://autokmdb.deepdata.hu/autokmdb";
// baseUrl = "http://localhost:8000";

const allLabels = useFetch(baseUrl + "/api/all_labels").data;
let allFiles = computed(() =>
  allLabels.value == null
    ? []
    : [{ name: "semmi", id: -1 }].concat(allLabels.value?.files)
);
let allDomains = computed(() =>
  allLabels.value == null
    ? []
    : [{ name: "mind", id: -1 }].concat(allLabels.value?.domains)
);
const selectedDomains = ref([{ name: "mind", id: -1 }]);
// Watch a selectedDomains változásaira
watch(
  selectedDomains,
  (newVal) => {
    const mindIndex = newVal.findIndex((domain) => domain.id === -1);
    const hasOtherSelections = newVal.some((domain) => domain.id !== -1);

    // Ha van másik kiválasztás és a 'mind' is benne van, távolítsuk el a 'mind'-t
    if (hasOtherSelections && mindIndex !== -1) {
      selectedDomains.value = newVal.filter((domain) => domain.id !== -1);
    }

    // Ha nincs semmi kiválasztva, válasszuk ki a 'mind'-t
    if (!hasOtherSelections && mindIndex === -1) {
      selectedDomains.value = [{ name: "mind", id: -1 }];
    }
  },
  { immediate: true }
);

const status = computed(() => statusItems.value[statusId.value].key);
const from = computed(() => format(selected.value.start, "yyyy-MM-dd"));
const to = computed(() => format(selected.value.end, "yyyy-MM-dd"));

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
      if (response.status >= 300) {
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

const {
  pending,
  data: articleQuery,
  refresh,
} = useLazyFetch(baseUrl + "/api/articles", {
  method: "POST",
  body: {
    page: page,
    status: status,
    domain: selectedDomains,
    from: from,
    to: to,
    q: q,
  },
  onResponse({ request, response, options }) {
    if (response.status >= 300) {
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

const selectedDomainAdd = ref(null);

function resetPageRefresh() {
  page.value = 1;
  refreshArticleCounts();
  refresh();
}

function refreshAll() {
  refreshArticleCounts();
  refresh();
}

function openNewUrl() {
  newUrl = "";
  isOpen.value = true;
}

async function deleteArticles() {
  console.log("hello");
  console.log(articles.value[0].selected);
  loadingDelete.value = true;
  for (const article of articles.value) {
    if (article.selected) {
      await $fetch(baseUrl + "/api/annote/negative", {
        method: "POST",
        body: { id: article.id, reason: 0 },
      });
    }
  }
  loadingDelete.value = false;
  resetPageRefresh();
}

async function addUrl() {
  isOpen.value = false;
  try {
    const { data } = await $fetch(baseUrl + "/api/add_url", {
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
      <UButton class="mr-1" @click="openNewUrl">Új cikk</UButton>
      <div>
        <UContainer class="my-1 flex lg:px-0 px-2 sm:px-0 ml-1">
          <div class="flex px-1">
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
                  ><Icon v-if="option.has_rss" name="mdi:rss" color="orange" />
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

          <UPopover class="px-1" :popper="{ placement: 'bottom-start' }">
            <UButton icon="i-heroicons-calendar-days-20-solid">
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
            class="px-1"
            name="q"
            v-model="q"
            color="primary"
            variant="outline"
            placeholder="Keresés..."
          />
          <UButton
            class="right-5 bottom-5 fixed z-10"
            v-if="articles && articles.some((v) => v.selected)"
            color="red"
            :loading="loadingDelete"
            @click="deleteArticles"
            >{{
              "Kijelöltet elutasít (" +
              articles.filter((v) => v.selected).length +
              ")"
            }}</UButton
          >
        </UContainer>
      </div>
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

    <UModal v-model="isOpenError">
      <div class="p-4">
        <h1 class="font-bold">{{ errorTitle }}</h1>
        <p class="py-5">{{ errorText }}</p>
        <UButton @click="isOpenError = false">Bezárás</UButton>
      </div>
    </UModal>

    <UTabs :items="statusItems" v-model="statusId" @change="resetPageRefresh">
      <template #item="{ item }" v-if="!pending">
        <UPagination
          class="p-4 justify-center"
          v-model="page"
          :page-count="10"
          :total="itemsCount"
          @click="refresh"
        />
        <Card
          class="flex justify-center"
          v-for="article in articles"
          :key="article.id"
          :article="article"
          :allLabels="allLabels"
          :allFiles="allFiles"
          :refresh="refreshAll"
        />
        <UPagination
          class="p-4 justify-center"
          v-model="page"
          :page-count="10"
          :total="itemsCount"
          @click="refresh"
        />
      </template>
      <template #item="{ item }" v-else>
        <UProgress animation="elastic" v-if="pending" />
      </template>
    </UTabs>
  </div>
</template>
