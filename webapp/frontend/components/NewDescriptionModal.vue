<script setup lang="ts">
import { $authFetch } from "~/auth_fetch";
import { descriptionEntityTypes, descriptionEntityType } from "~/utils/descriptions";

const props = defineProps<{
  isOpen: boolean;
  allLabels: any;
}>();

const emit = defineEmits<{
  (e: "update:isOpen", value: boolean): void;
  (e: "queued"): void;
  (e: "error", error: any): void;
}>();

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;

const entityType = ref("person");
const entity = ref<any | null>(null);
const preview = ref<any | null>(null);
const loadingPreview = ref(false);
const submitting = ref(false);

const entities = computed(() => {
  const key = descriptionEntityType(entityType.value)!.labelsKey;
  const list: any[] = props.allLabels?.[key] ?? [];
  return [...list].sort((a, b) => articleCount(b) - articleCount(a));
});

const previewText = computed(() =>
  preview.value ? `${preview.value.system_instruction}\n\n---\n\n${preview.value.prompt}` : ""
);

watch(entityType, () => {
  entity.value = null;
});
watch(entity, () => {
  preview.value = null;
});

function articleCount(e: any): number {
  return e.count ?? e.article_count ?? 0;
}

// There are tens of thousands of persons, so only the most used matches are listed.
function searchEntities(q: string) {
  const query = q.trim().toLocaleLowerCase("hu");
  return entities.value
    .filter((e) => e.name?.toLocaleLowerCase("hu").includes(query))
    .slice(0, 50);
}

function close() {
  emit("update:isOpen", false);
}

async function loadPreview() {
  loadingPreview.value = true;
  try {
    preview.value = await $authFetch(baseUrl + "/api/descriptions/prompt", {
      query: { entity_type: entityType.value, entity_id: entity.value.id },
    });
  } catch (error) {
    emit("error", error);
  } finally {
    loadingPreview.value = false;
  }
}

async function submit() {
  submitting.value = true;
  try {
    await $authFetch(baseUrl + "/api/descriptions", {
      method: "POST",
      body: { entity_type: entityType.value, entity_id: entity.value.id },
    });
    entity.value = null;
    emit("queued");
    close();
  } catch (error) {
    emit("error", error);
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <UModal :model-value="isOpen" @update:model-value="emit('update:isOpen', $event)" :ui="{ width: 'sm:max-w-3xl' }">
    <div class="p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Új leírás generálása</h2>
        <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="close" />
      </div>

      <div class="flex gap-2 flex-wrap">
        <USelect v-model="entityType" :options="descriptionEntityTypes" option-attribute="label"
          value-attribute="value" class="w-40" />
        <!-- Recreated on type change, the search results do not follow the entity list otherwise. -->
        <USelectMenu :key="entityType" v-model="entity" :searchable="searchEntities"
          searchable-placeholder="Keresés..." option-attribute="name" class="flex-grow min-w-64"
          :loading="!allLabels">
          <template #label>
            <span v-if="entity" class="truncate">{{ entity.name }}</span>
            <span v-else class="text-gray-500">Válassz ki egyet...</span>
          </template>
          <template #option="{ option }">
            <span class="truncate">{{ option.name }}</span>
            <span class="text-xs text-gray-500 flex-shrink-0">{{ articleCount(option).toLocaleString('hu-HU') }} cikk</span>
          </template>
        </USelectMenu>
      </div>

      <p class="text-sm text-gray-500 mt-3">
        A generálás a háttérben fut, a kész javaslat az Ellenőrizendő fülön jelenik meg. A prompt előnézet nem
        küld kérést a modellnek.
      </p>

      <div v-if="preview" class="mt-4">
        <p class="text-sm text-gray-600 mb-1">
          {{ preview.article_count }} KMDB cikk a promptban,
          {{ preview.web_search ? "a további forrásokat a modell webes kereséssel keresi meg." : "a modell nem keres a weben, csak ezekből dolgozik." }}
        </p>
        <pre class="text-xs whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded p-2 max-h-96 overflow-y-auto">{{ previewText }}</pre>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <UButton color="gray" variant="outline" :disabled="!entity" :loading="loadingPreview" @click="loadPreview">
          Prompt előnézet
        </UButton>
        <UButton :disabled="!entity" :loading="submitting" @click="submit">Generálás indítása</UButton>
      </div>
    </div>
  </UModal>
</template>
