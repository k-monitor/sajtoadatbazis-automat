<script setup lang="ts">
definePageMeta({
  colorMode: "light",
});

import { $authFetch } from "~/auth_fetch";
import {
  descriptionEntityType,
  descriptionStatuses,
  formatDescriptionDate,
} from "~/utils/descriptions";

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;
const toast = useToast();

const PAGE_SIZE = 20;
const tabs = [
  { key: "review", label: "Ellenőrizendő", icon: "i-heroicons-question-mark-circle-solid" },
  { key: "processing", label: "Feldolgozás alatt", icon: "i-heroicons-clock" },
  { key: "all", label: "Mind", icon: "i-heroicons-bars-3" },
];

const isAuthenticated = ref(true);
const tabIndex = ref(0);
const page = ref(1);
const pages = ref(0);
const descriptions = ref<any[]>([]);
const counts = ref<Record<string, number> | null>(null);
const pending = ref(false);
const allLabels = ref<any | null>(null);
const isOpenNew = ref(false);
const openedId = ref<number | null>(null);
const chatgptStatus = ref<any | null>(null);
const isOpenChatGPT = ref(false);

// Only shown if the descriptions are generated with the ChatGPT plan (DESCRIPTION_PROVIDER=chatgpt).
const usesChatGPT = computed(() => chatgptStatus.value?.provider === "chatgpt");
const chatgptReady = computed(
  () => chatgptStatus.value?.connected && chatgptStatus.value?.plan_usage && !chatgptStatus.value?.problem
);
const chatgptLabel = computed(() => {
  const status = chatgptStatus.value;
  if (!status?.connected) return "ChatGPT nincs csatlakoztatva";
  if (!status.plan_usage) return "ChatGPT-előfizetés nincs engedélyezve";
  if (status.problem) return "ChatGPT: a generálás szünetel";
  return "ChatGPT-előfizetés használatban";
});

const tabItems = computed(() =>
  tabs.map((tab) => ({ ...tab, count: counts.value ? counts.value[tab.key] : null }))
);

function handleError(error: any) {
  if (error?.status === 401) {
    isAuthenticated.value = false;
    return;
  }
  toast.add({
    title: "Hiba" + (error?.status ? " " + error.status : ""),
    description: error?.data?.error || String(error),
    color: "red",
  });
}

async function load(silent = false) {
  if (!silent) pending.value = true;
  try {
    const response: any = await $authFetch(baseUrl + "/api/descriptions", {
      query: { status: tabs[tabIndex.value].key, page: page.value },
    });
    descriptions.value = response.descriptions;
    pages.value = response.pages;
    counts.value = response.counts;
  } catch (error) {
    handleError(error);
  } finally {
    pending.value = false;
  }
}

async function loadChatGPT() {
  try {
    chatgptStatus.value = await $authFetch(baseUrl + "/api/chatgpt");
  } catch (error) {
    handleError(error);
  }
}

function changePage(newPage: number) {
  page.value = newPage;
  load();
}

// UTabs emits change before updating its v-model.
function changeTab(index: number) {
  tabIndex.value = index;
  page.value = 1;
  load();
}

async function openNew() {
  isOpenNew.value = true;
  if (allLabels.value === null) {
    try {
      allLabels.value = await $authFetch(baseUrl + "/api/all_labels");
    } catch (error) {
      handleError(error);
    }
  }
}

function handleQueued() {
  toast.add({ title: "Sorba állítva", description: "A javaslat a háttérben készül el.", timeout: 3000 });
  load();
}

function handleChanged(action: string) {
  const titles: Record<string, string> = {
    accept: "Leírás elfogadva",
    reject: "Javaslat elutasítva",
    retry: "Újragenerálás sorba állítva",
  };
  toast.add({ title: titles[action], timeout: 3000 });
  load();
}

function handleLoginSuccess() {
  isAuthenticated.value = true;
  document.location.reload();
}

// Picks up the suggestions finished in the background while something is being processed.
let pollTimer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  load();
  loadChatGPT();
  pollTimer = setInterval(() => {
    if (counts.value?.processing && openedId.value === null && !isOpenNew.value) {
      load(true);
      if (usesChatGPT.value && !isOpenChatGPT.value) loadChatGPT();
    }
  }, 15000);
});
onBeforeUnmount(() => clearInterval(pollTimer));
</script>

<template>
  <div>
    <LoginForm v-if="!isAuthenticated" @loginSuccess="handleLoginSuccess" />

    <template v-else>
      <UContainer class="my-1 pb-2 border-b border-gray-200 dark:border-gray-700 flex flex-wrap lg:px-0 px-4 sm:px-0 ml-1 max-w-full items-center gap-2">
        <div class="flex items-center my-1">
          <PageTitle :baseUrl="baseUrl" />
          <span class="text-xl text-gray-500 select-none">/ leírások</span>
        </div>

        <UButton class="ml-2 h-fit" size="sm" @click="openNew">
          <Icon name="mdi:plus" class="mr-1" />
          Új leírás
        </UButton>

        <template v-if="usesChatGPT">
          <UButton v-if="chatgptReady" class="h-fit" size="sm" color="gray" variant="ghost"
            icon="i-heroicons-check-circle" @click="isOpenChatGPT = true">
            {{ chatgptLabel }}
          </UButton>
          <UButton v-else class="h-fit" size="sm" color="amber" variant="soft"
            icon="i-heroicons-exclamation-triangle" @click="isOpenChatGPT = true">
            {{ chatgptLabel }}
          </UButton>
        </template>
      </UContainer>

      <ChatGPTModal :isOpen="isOpenChatGPT" :status="chatgptStatus" @update:isOpen="isOpenChatGPT = $event"
        @update:status="chatgptStatus = $event" @error="handleError" />

      <NewDescriptionModal :isOpen="isOpenNew" :allLabels="allLabels" @update:isOpen="isOpenNew = $event"
        @queued="handleQueued" @error="handleError" />

      <DescriptionReviewModal :descriptionId="openedId" @close="openedId = null" @changed="handleChanged"
        @error="handleError" />

      <UTabs
        :items="tabItems"
        v-model="tabIndex"
        @change="changeTab"
        :ui="{
          wrapper: 'space-y-2',
          list: {
            base: 'relative',
            width: 'w-auto',
            background: 'bg-transparent',
            rounded: 'rounded-none',
            shadow: '',
            padding: 'p-0',
            height: 'h-auto',
            marker: {
              wrapper: 'absolute top-[unset] bottom-0 left-0 duration-200 ease-out focus:outline-none',
              base: 'w-full h-full',
              background: 'bg-transparent',
              rounded: 'rounded-none',
              shadow: '',
            },
            tab: {
              base: 'relative inline-flex items-center justify-center flex-shrink-0 w-auto ui-focus-visible:outline-0 ui-focus-visible:ring-0 ui-not-focus-visible:outline-none focus:outline-none disabled:cursor-not-allowed disabled:opacity-75 transition-colors duration-200 ease-out',
              background: '',
              active: 'text-gray-900 dark:text-white font-bold border-b-2 border-green-500',
              inactive: 'text-gray-600 dark:text-gray-300 hover:text-gray-900 border-b-2 border-transparent',
              height: 'h-10',
              padding: 'px-3',
              size: 'text-sm',
              font: '',
              rounded: 'rounded-none',
              shadow: '',
              icon: 'flex-shrink-0 w-4 h-4 text-gray-500 dark:text-gray-500 me-2',
            },
          },
        }"
        class="border-b border-gray-200 dark:border-gray-700"
      >
        <template #default="{ item, selected }">
          <span class="truncate">{{ item.label }}</span>
          <span
            class="ml-2 px-1.5 py-0.5 text-xs rounded font-medium"
            :class="selected ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'"
          >{{ item.count !== null ? item.count.toLocaleString('hu-HU') : '...' }}</span>
        </template>
      </UTabs>

      <UProgress v-if="pending" animation="elastic" />
      <div v-else class="flex flex-col items-center px-4">
        <UPagination v-if="pages > 1" class="p-4 justify-center" :model-value="page" :page-count="PAGE_SIZE"
          :total="pages * PAGE_SIZE" @update:model-value="changePage" />

        <p v-if="!descriptions.length" class="text-gray-500 my-8">Nincs itt semmi.</p>

        <button
          v-for="description in descriptions"
          :key="description.id"
          type="button"
          class="w-full max-w-3xl text-left border border-gray-200 rounded-lg p-3 my-1 hover:bg-gray-50 transition-colors"
          @click="openedId = description.id"
        >
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-1.5 py-0.5 text-xs rounded font-medium"
              :class="descriptionEntityType(description.entity_type)?.badgeClass">
              {{ descriptionEntityType(description.entity_type)?.label }}
            </span>
            <span class="font-semibold">{{ description.entity_name }}</span>
            <span class="ml-auto px-1.5 py-0.5 text-xs rounded font-medium"
              :class="descriptionStatuses[description.status]?.badgeClass">
              {{ descriptionStatuses[description.status]?.label }}
            </span>
          </div>
          <p v-if="description.status === 'error'" class="text-sm text-red-600 mt-1 line-clamp-2">{{ description.error }}</p>
          <p v-else-if="description.preview" class="text-sm text-gray-600 mt-1 line-clamp-2">{{ description.preview }}</p>
          <p class="text-xs text-gray-400 mt-1">
            {{ formatDescriptionDate(description.mod_time) }}<template v-if="description.mod_name"> · {{ description.mod_name }}</template>
          </p>
        </button>

        <UPagination v-if="pages > 1" class="p-4 justify-center" :model-value="page" :page-count="PAGE_SIZE"
          :total="pages * PAGE_SIZE" @update:model-value="changePage" />
      </div>
    </template>
  </div>
</template>

<style scoped>
:deep([role="tablist"]) {
  display: flex !important;
  justify-content: flex-start;
  grid-template-columns: none !important;
}
</style>
