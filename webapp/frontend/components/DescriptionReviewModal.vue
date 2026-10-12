<script setup lang="ts">
import { $authFetch } from "~/auth_fetch";
import {
  descriptionEntityType,
  descriptionStatuses,
  linkedUrls,
  normalizeUrl,
  formatDescriptionDate,
} from "~/utils/descriptions";

const props = defineProps<{
  descriptionId: number | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "changed", action: string): void;
  (e: "error", error: any): void;
}>();

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;
const toast = useToast();

const description = ref<any | null>(null);
// The HTML in the editor, the generated markdown is converted to HTML by the backend.
const text = ref("");
const loading = ref(false);
const acting = ref<string | null>(null);

const isReview = computed(() => description.value?.status === "review");
const canRetry = computed(() => ["review", "rejected", "error"].includes(description.value?.status));
// Rows generated before the Google Search grounding have no kind, they only have KMDB articles.
const kmdbSources = computed(() => (description.value?.sources ?? []).filter((s: any) => s.kind !== "search"));
const searchSources = computed(() => (description.value?.sources ?? []).filter((s: any) => s.kind === "search"));
const sourceUrls = computed(
  () => new Set((description.value?.sources ?? []).map((s: any) => normalizeUrl(s.url)))
);
// The teaser and the bodytext are shown once if they are the same.
const currentBlocks = computed(() => {
  const teaser = description.value?.current_teaser ?? "";
  const bodytext = description.value?.current_bodytext ?? "";
  if (normalizeWhitespace(teaser) === normalizeWhitespace(bodytext)) {
    return bodytext ? [{ label: "Jelenlegi leírás (teaser és bodytext)", text: bodytext }] : [];
  }
  return [
    { label: "Jelenlegi teaser", text: teaser },
    { label: "Jelenlegi bodytext", text: bodytext },
  ].filter((block) => block.text);
});
const hasBackup = computed(
  () => description.value?.status === "accepted" && (description.value.old_teaser || description.value.old_bodytext)
);
// Every claim should cite a KMDB article from the prompt or a page found by web search, anything
// else is probably made up.
const unknownUrls = computed(() =>
  linkedUrls(text.value).filter((url) => !sourceUrls.value.has(normalizeUrl(url)))
);

watch(
  () => props.descriptionId,
  async (id) => {
    description.value = null;
    if (id === null) return;
    loading.value = true;
    try {
      description.value = await $authFetch(`${baseUrl}/api/descriptions/${id}`);
      text.value = description.value.final_description ?? description.value.suggestion_html ?? "";
    } catch (error) {
      emit("error", error);
      emit("close");
    } finally {
      loading.value = false;
    }
  },
  { immediate: true }
);

function normalizeWhitespace(value: string): string {
  return value.split(/\s+/).join(" ").trim();
}

async function act(action: "accept" | "reject" | "retry") {
  acting.value = action;
  try {
    await $authFetch(`${baseUrl}/api/descriptions/${props.descriptionId}/${action}`, {
      method: "POST",
      body: action === "accept" ? { description: text.value } : {},
    });
    emit("changed", action);
    emit("close");
  } catch (error) {
    emit("error", error);
  } finally {
    acting.value = null;
  }
}

async function copyText() {
  await navigator.clipboard.writeText(text.value);
  toast.add({ title: "Vágólapra másolva", timeout: 2000 });
}
</script>

<template>
  <UModal :model-value="descriptionId !== null" @update:model-value="(open: boolean) => !open && emit('close')"
    :ui="{ width: 'sm:max-w-7xl' }">
    <div class="p-6 max-h-[90vh] overflow-y-auto">
      <UProgress v-if="loading" animation="elastic" />

      <template v-else-if="description">
        <div class="flex items-center gap-2 flex-wrap pb-3 border-b border-gray-200">
          <span class="px-1.5 py-0.5 text-xs rounded font-medium"
            :class="descriptionEntityType(description.entity_type)?.badgeClass">
            {{ descriptionEntityType(description.entity_type)?.label }}
          </span>
          <h2 class="text-xl font-bold">{{ description.entity_name }}</h2>
          <span class="px-1.5 py-0.5 text-xs rounded font-medium" :class="descriptionStatuses[description.status]?.badgeClass">
            {{ descriptionStatuses[description.status]?.label }}
          </span>
          <UButton v-if="description.url" class="ml-auto" size="sm" color="gray" variant="outline"
            icon="i-heroicons-arrow-top-right-on-square" :to="description.url" target="_blank" rel="noopener noreferrer">
            Megnyitás a KMDB-ben
          </UButton>
          <UButton :class="description.url ? '' : 'ml-auto'" icon="i-heroicons-x-mark" color="gray" variant="ghost"
            @click="emit('close')" />
        </div>

        <div class="grid md:grid-cols-5 gap-4 mt-4">
          <div class="md:col-span-2">
            <template v-for="block in currentBlocks" :key="block.label">
              <p class="font-bold mb-1">{{ block.label }}</p>
              <div class="text-sm whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded p-3 mb-3">{{ block.text }}</div>
            </template>
            <template v-if="!currentBlocks.length">
              <p class="font-bold mb-1">Jelenlegi leírás</p>
              <p class="text-sm text-gray-500 italic">Nincs leírás.</p>
            </template>
          </div>

          <div class="md:col-span-3 min-w-0">
            <div class="flex justify-between items-center mb-1">
              <p class="font-bold">{{ description.status === "accepted" ? "Elfogadott leírás" : "Javaslat" }}</p>
              <UButton v-if="text" size="xs" color="gray" variant="ghost" icon="i-heroicons-clipboard-document"
                @click="copyText">
                HTML másolása
              </UButton>
            </div>
            <p v-if="description.status === 'error'"
              class="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3 whitespace-pre-wrap">{{ description.error }}</p>
            <p v-else-if="description.status === 'queued'" class="text-sm text-gray-500 italic">
              A javaslat generálása folyamatban van.
            </p>
            <DescriptionHtmlEditor v-else v-model="text" :editable="isReview" />
            <p v-if="isReview" class="text-xs text-gray-500 mt-1">
              Elfogadáskor a KMDB-ben a teaser és a bodytext is erre cserélődik, a korábbi tartalmuk mentésre kerül.
            </p>

            <div v-if="unknownUrls.length" class="mt-2 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded p-3">
              <p class="font-semibold">Nem a KMDB cikkek és nem a webes találatok közül való források, ellenőrizd őket:</p>
              <ul class="list-disc ml-5 mt-1">
                <li v-for="url in unknownUrls" :key="url" class="break-all">
                  <a :href="url" target="_blank" rel="noopener noreferrer" class="underline">{{ url }}</a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <details v-if="kmdbSources.length" class="mt-4">
          <summary class="cursor-pointer font-bold select-none">
            A promptban szereplő KMDB cikkek ({{ kmdbSources.length }})
          </summary>
          <ul class="text-sm mt-2 max-h-64 overflow-y-auto space-y-1">
            <li v-for="source in kmdbSources" :key="source.url">
              <span class="text-gray-500">{{ source.date }} {{ source.newspaper }}</span> –
              <a :href="source.url" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">
                {{ source.title || source.url }}
              </a>
            </li>
          </ul>
        </details>
        <details v-if="searchSources.length" class="mt-2">
          <summary class="cursor-pointer font-bold select-none">
            Webes találatok, amelyekre a válasz támaszkodik ({{ searchSources.length }})
          </summary>
          <ul class="text-sm mt-2 max-h-64 overflow-y-auto space-y-1">
            <li v-for="source in searchSources" :key="source.url" class="break-all">
              <span class="text-gray-500">{{ source.title }}</span> –
              <a :href="source.url" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">
                {{ source.url }}
              </a>
            </li>
          </ul>
        </details>
        <details v-if="hasBackup" class="mt-2">
          <summary class="cursor-pointer font-bold select-none">Felülírt korábbi teaser és bodytext (HTML mentés)</summary>
          <p class="text-sm font-semibold mt-2">teaser</p>
          <pre class="text-xs whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded p-2 max-h-64 overflow-y-auto">{{ description.old_teaser }}</pre>
          <p class="text-sm font-semibold mt-2">bodytext</p>
          <pre class="text-xs whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded p-2 max-h-64 overflow-y-auto">{{ description.old_bodytext }}</pre>
        </details>
        <details v-if="description.prompt" class="mt-2">
          <summary class="cursor-pointer font-bold select-none">Prompt</summary>
          <pre class="text-xs whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded p-2 mt-2 max-h-96 overflow-y-auto">{{ description.prompt }}</pre>
        </details>

        <p class="text-xs text-gray-400 mt-3">
          Létrehozva: {{ formatDescriptionDate(description.cre_time) }} · Módosítva:
          {{ formatDescriptionDate(description.mod_time) }}<template v-if="description.mod_name"> ({{ description.mod_name }})</template>
          <template v-if="description.model">
            · {{ description.model }}, tokenek: {{ description.prompt_tokens }} prompt, {{ description.thinking_tokens ?? 0 }}
            gondolkodás, {{ description.response_tokens }} válasz
          </template>
        </p>

        <div class="flex justify-between mt-4">
          <UButton color="gray" @click="emit('close')">Mégse</UButton>
          <div class="flex gap-2">
            <UButton v-if="canRetry" color="gray" variant="outline" icon="i-heroicons-arrow-path"
              :loading="acting === 'retry'" :disabled="acting !== null" @click="act('retry')">
              Újragenerálás
            </UButton>
            <UButton v-if="isReview" color="red" :loading="acting === 'reject'" :disabled="acting !== null"
              @click="act('reject')">
              Elutasít
            </UButton>
            <UButton v-if="isReview" :loading="acting === 'accept'" :disabled="acting !== null || !text.trim()"
              @click="act('accept')">
              Elfogad
            </UButton>
          </div>
        </div>
      </template>
    </div>
  </UModal>
</template>
