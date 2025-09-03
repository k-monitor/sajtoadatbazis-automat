<template>
  <div class="p-4" color="gray">
    <div class="max-w-2xl w-full rounded overflow-hidden shadow-lg mb-4 p-4">
      <p class="inline">
        <UBadge class="m-1 inline p-2" color="gray">
          <UTooltip v-if="article.skip_reason == 2" :text="'átvett cikk'">
            <Icon size="1.2em" name="mdi:alert-circle-outline" color="orange" />
          </UTooltip>
          <UTooltip v-else-if="article.skip_reason == 3" :text="'letöltési hiba'">
            <Icon size="1.2em" name="mdi:alert-circle-outline" class="text-orange-500" />
          </UTooltip>
          <UTooltip v-else-if="article.skip_reason == 4" :text="'feldolgozási hiba'">
            <Icon size="1.2em" name="mdi:alert-circle-outline" color="orange" />
          </UTooltip>
          <UTooltip v-else-if="article.processing_step < 4" :text="'feldolgozás alatt'">
            <Icon size="1.2em" name="mdi:database-clock-outline" class="text-gray-500" />
          </UTooltip>
          <UTooltip v-else-if="
            article.annotation_label == null &&
            article.classification_label == 0
          " :text="'nem illik az adatbázisba'">
            <Icon size="1.2em" name="mdi:window-close" class="text-gray-500" />
          </UTooltip>
          <UTooltip v-else-if="
            article.annotation_label == null &&
            article.classification_label == 1
          " :text="article.mod_name ? ('ellenőrizendő, hozzáadta: ' + article.mod_name) : 'ellenőrizendő'">
            <Icon size="1.2em" name="mdi:question-mark" class="text-gray-500" />
          </UTooltip>
          <UTooltip v-else-if="article.annotation_label == 0"
            :text="'elutasított : ' + (article.mod_name ?? '') + ' : ' + reasons[String(article.negative_reason)]">
            <Icon size="1.2em" name="mdi:database-remove-outline" class="text-red-500" />
          </UTooltip>
          <UTooltip v-else-if="article.annotation_label == 1" :text="'elfogadott : ' + (article.mod_name ?? '')">
            <Icon size="1.2em" name="mdi:database-check-outline" class="text-green-500" />
          </UTooltip>
        </UBadge>
        <UButton class="m-1 px-2 py-1 inline" color="blue"
          @click="() => $emit('update:filter_newspaper', { name: article.newspaper_name, id: article.newspaper_id })">
          {{
            article.newspaper_name }} </UButton>
        <a :href="article.url" target="_blank" class="font-bold text-xl mb-2 ml-1"
          :style="article.group_id && article.annotation_label != null ? 'color: #888' : ''">{{
            article.title
          }}</a>

      </p>
      <UBadge v-if="article.source == 1" class="m-1" color="orange">
        manuálisan hozzáadott
      </UBadge>
      <p v-if="!is_small" class="text-base text-pretty">{{ article.description }}</p>
      <p class="text-base text-right py-1">{{ article.date }}</p>

      <UContainer v-if="
        article.processing_step >= 4 && article.skip_reason == null && !is_small
      " class="flex justify-between px-0 sm:px-0 lg:px-0">
        <UDropdown label="Elutasít" :items="items" :popper="{ placement: 'bottom-end' }" v-if="article.annotation_label != null">
          <UButton color="red"
            :label="article.annotation_label == null ? 'Elutasít' : article.annotation_label == 1 ? 'Mégis elutasít' : reasons[String(article.negative_reason)]"
            trailing-icon="i-heroicons-chevron-down-20-solid" />
          <template #item="{ item }">
            <span class="">{{ item.label }}</span>
          </template>
        </UDropdown>
        <div class="flex gap-2">
          <UDropdown
            v-if="article.annotation_label == null"
            :items="negativeItems"
            :popper="{ placement: 'bottom-end' }"
          >
            <UButton
              color="red"
              label="Megjelöl"
              trailing-icon="i-heroicons-chevron-down-20-solid"
            />
            <template #item="{ item }">
              <span class="">{{ item.label }}</span>
            </template>
          </UDropdown>
          <UBadge v-if="article.pending_negative_reason != null" color="red" variant="soft" class="flex items-center gap-1">
            {{ negativeReasonLabel(article.pending_negative_reason) }}
            <Icon
              name="mdi:close"
              size="14"
              class="cursor-pointer opacity-80 hover:opacity-100"
              title="Megjelölés törlése"
              @click.stop="clearPendingNegative"
            />
          </UBadge>
        </div>
        <p class="items-center p-2 ml-auto"
          title="Teszt: ez a szám azt mutatja, algoritmusaink szerint mennyire illik a cikk a módszertanba (100% - nagyon, 0% - kevésbé)">
          {{ Math.round(article.classification_score * 100) }}%
        </p>
        <UButton v-if="article.annotation_label == null && article.classification_label == 0" @click="processAndAccept"
          :loading="accepting" class="" :disabled="allLabels == null">Feldolgoz és átsorol</UButton>
        <UButton v-if="article.annotation_label == null && article.classification_label == 1" @click="openModal"
          :loading="isOpening" class="" :disabled="allLabels == null">Szerkesztés</UButton>
        <UButton v-if="article.annotation_label == 1" @click="openModal" :loading="isOpening" :disabled="allLabels == null" class="">Szerkesztés
        </UButton>
        <UButton v-if="article.annotation_label == 0" @click="openModal" :loading="isOpening" :disabled="allLabels == null" class="">Mégis elfogad
        </UButton>
      </UContainer>
      <div class="flex justify-between" v-if="!is_small">
        <UButton v-if="article.skip_reason >= 1" color="orange" @click="retryArticle">Újra feldolgoz</UButton>
        <UButton v-if="(article.skip_reason >= 1)" @click="forceAccept" class="ml-auto r-0" color="purple">{{
          "Szerkesztésre küld" }}</UButton>
      </div>
      <div class="flex justify-between" v-else>
        <UButton v-if="!(article.negative_reason == 1 && article.annotation_label == 0)" color="red" @click="toPool">
          Hasonló tartalom
        </UButton>
        <div class="flex items-center gap-2 ml-auto">
          <UBadge v-if="article.pending_negative_reason != null" color="red" variant="soft" class="flex items-center gap-1">
            {{ negativeReasonLabel(article.pending_negative_reason) }}
            <Icon
              name="mdi:close"
              size="14"
              class="cursor-pointer opacity-80 hover:opacity-100"
              title="Megjelölés törlése"
              @click.stop="clearPendingNegative"
            />
          </UBadge>
          <UButton @click="pickOut" class="ml-auto r-0" color="green">Elfogad</UButton>
        </div>
      </div>
      <div v-if="!is_small">
        <Card
          v-for="gArticle in article.groupedArticles"
          :is_small="true"
          :article="gArticle"
          :key="gArticle.id"
          :allLabels="allLabels"
          :keywordSynonyms="keywordSynonyms"
          :allFiles="allFiles"
          :refresh="refresh"
          class="w-full max-w-2xl pr-0 pl-8"
        />
      </div>
    </div>


    <UModal v-model="isOpen" :ui="{ padding: 'p-0 sm:p-4', width: 'sm:max-w-7xl' }">
      <div class="p-4 w-full">
        <div class="my-2 flex justify-center px-0 sm:px-0 lg:px-0 flex-col md:flex-row">
          <div class="max-w-2xl mx-4 flex-grow">
            <p class="font-bold">Cím:</p>
            <UTextarea class="my-2 min-h-0" :rows="1" autoresize v-model="article.title" />
            <p class="font-bold">URL:</p>
            <UInput class="my-2" v-model="article.url" />
            <p class="font-bold">Leírás:</p>
            <UTextarea class="my-2" resize v-model="article.description" />
            <div class="flex justify-between">
              <p class="font-bold">Szöveg ({{ articleLength }}):</p>
              <div class="flex items-center">
                <p>szerkeszt:</p>
                <UToggle class="m-2" size="md" color="primary" v-model="edit" />
              </div>
            </div>
            <UTextarea v-if="edit" class="my-2" v-model="article.text" :rows="20" />
            <div v-if="!edit" style="overflow-y: scroll; height: 400px">
              <span class="my-2" v-html="richText"></span>
            </div>
            <a v-if="article.is_paywalled" :href="article.url" target="_blank">
              <Icon title="Valószínűsíthetően a cikk teljes szövege paywall/bejelentkezés mögött található!"
                name="mdi:dollar" size="26" style="color: #f59e0b;"></Icon>
            </a>
          </div>

          <div class="max-w-lg mx-4 flex-grow min-w-80">
            <SelectMenu :list="allPersons" type="személy" :creatable="true" :positive-list="positivePersons"
              @update:positiveList="updatePositivePersons" :labels="allLabels['person']" />
            <SelectMenu :list="allInstitutions" type="intézmény" :creatable="true" :positive-list="positiveInstitutions"
              @update:positiveList="updatePositiveInstitutions" :labels="allLabels['institution']" />
            <SelectMenu :list="allPlaces" type="helyszín" :creatable="false" :positive-list="positivePlaces"
              @update:positiveList="updatePositivePlaces" :labels="allLabels['place']" />
            <SelectMenu :list="allOthers" type="egyéb" :creatable="false" :positive-list="positiveOthers"
              @update:positiveList="updatePositiveOthers" :labels="allLabels['keywords']" />
            <p class="font-bold">Kategória:</p>
            <USelect class="my-2" v-model="category" :options="categories" option-attribute="name"
              value-attribute="id" />
            <SelectMenu :list="allFiles" type="akta" :creatable="false" :positive-list="positiveFiles"
              @update:positiveList="updatePositiveFiles" :labels="allLabels['files']" />
            <p>publikálás: {{ article.article_date }}</p>
            <p>{{ errorText }}</p>
            <UButton class="my-5" v-if="article.annotation_label == 1" target="_blank"
              :to="`${config.public.adminUrl}?mod=news&action=news&do=news&news_id=${article.news_id}`">
              szerkesztés az adminban
            </UButton>
          </div>
        </div>
        <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0 mx-4">
          <UButton color="gray" @click="closeModal">Mégse</UButton>

          <div class="my-2 flex justify-between">
            <UDropdown label="Elutasít" :items="items" :popper="{ placement: 'bottom-end' }"
              v-if="article.annotation_label != 0">
              <UButton color="red" :label="article.annotation_label == null ? 'Elutasít' : 'Mégis elutasít'"
                trailing-icon="i-heroicons-chevron-down-20-solid" />
              <template #item="{ item }">
                <span class="">{{ item.label }}</span>
              </template>
            </UDropdown>
            <div class="mx-4 flex">
              <p class="mr-2 my-auto">Aktív: </p>
              <UToggle class="my-auto" v-model="is_active" />
            </div>
            <UButton @click="submitArticle" :loading="submitted">Elfogad</UButton>
          </div>
        </UContainer>
        <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0 mx-4">
          <UAlert v-if="showThanks" color="primary" icon="i-heroicons-heart" :title="thanksMessage" />
        </UContainer>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { set } from "date-fns";
import { $authFetch } from "~/auth_fetch";

const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;

function formatDate(apiDateString: string): string {
  const date = new Date(apiDateString);

  // Define an options object for the Hungarian format and Budapest time zone
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Europe/Budapest',
  };

  // Format the date using Intl.DateTimeFormat
  const formatter = new Intl.DateTimeFormat('hu-HU', options);
  const parts = formatter.formatToParts(date);

  const getPart = (t: string) => parts.find(p => p.type === t)?.value ?? '';
  // Rebuild the string in "YYYY. MM. DD. HH:mm:ss" format
  const formattedDate = `${getPart('year')}. ${getPart('month')}. ${getPart('day')}. ${getPart('hour')}:${getPart('minute')}:${getPart('second')}`;

  console.log(formattedDate);
  return formattedDate;
}

function getRandomThanks() {
  const defaultThanks = "Köszi, hogy ezzel a cikkel is bővítetted a K-Monitor sajtóadatbázisát!";
  const otherThanks = [
    "Köszi a beküldést, köszi a munkát!",
    "Ennek a cikknek az elfogadásával Magyarország legnagyobb közpénzes, korrupciós adatbázisát bővítetted! Köszi!",
    "Együtt építjük a sajtóadatbázist. Köszi!",
    "A K-Monitor sajtóadatbázisa 2007 óta gyűjti a közpénzes, korrupciós cikkeket. Köszi, hogy része vagy!",
  ];

  return Math.random() < 0.5 ? defaultThanks : otherThanks[Math.floor(Math.random() * otherThanks.length)];
}

const thanksMessage = ref(getRandomThanks());

const showThanks = ref(false);
const edit = ref(false);
let accepting = ref(false);
let category = ref(0);
let categories = ref([
  { name: "Hírek/Magyar hírek", id: 0 },
  { name: "Hírek/EU hírek", id: 1 },
  { name: "Hírek/Világ hírek", id: 2 },
]);

async function forceAccept() {
  console.log("force accept");
  accepting.value = true;
  await postUrl(baseUrl + "/api/annote/force_accept", {
    method: "POST",
    body: { id: article.value.id },
  });
  refresh();
  accepting.value = false;
}

async function processAndAccept() {
  accepting.value = true;
  await postUrl(baseUrl + "/api/process_and_accept", {
    method: "POST",
    body: { article_id: article.value.id },
  });
  refresh();
  accepting.value = false;
}

async function toPool() {
  // await postUrl(baseUrl + "/api/annote/negative", {
  //   method: "POST",
  //   body: { id: article.value.id, reason: 1 }, // átvett
  // });
  // refresh();
  setPendingNegative(1);
}

async function pickOut() {
  $authFetch(baseUrl + "/api/annote/pick_out", {
    method: "POST",
    body: { id: article.value.id },
  });
  refresh();
}

function setPendingNegative(reason: number) {
  // mark the article with the chosen reason; bulk action will submit later
  article.value.pending_negative_reason = reason;
  if (article.value.original) article.value.original.pending_negative_reason = reason;
}

function clearPendingNegative() {
  article.value.pending_negative_reason = null;
  if (article.value.original) article.value.original.pending_negative_reason = null;
}

const reasons: Record<string, string> = { '0': 'Nem releváns', '1': 'Átvett', '2': 'Külföldi', '3': 'Már szerepel', '100': 'Egyéb' }

async function annoteNegative(reason: number) {
  showThanks.value = true;
  thanksMessage.value = getRandomThanks();
  await postUrl(baseUrl + "/api/annote/negative", {
    method: "POST",
    body: { id: article.value.id, reason: reason },
  });
  refresh();
  showThanks.value = false;
}

const items = [
  [
    {
      label: "Nem releváns",
      slot: "item",
      click: () => annoteNegative(0),
    },
    {
      label: "Átvett",
      slot: "item",
      click: () => annoteNegative(1),
    },
    {
      label: "Már szerepel",
      slot: "item",
      click: () => annoteNegative(3),
    },
    {
      label: "Külföldi",
      slot: "item",
      click: () => annoteNegative(2),
    },
    {
      label: "Egyéb",
      slot: "item",
      click: () => annoteNegative(100),
    }
  ],
];

// Dropdown items for marking negative reason without immediate submit
const negativeItems = [
  [
    { label: 'Nem releváns', slot: 'item', click: () => setPendingNegative(0) },
    { label: 'Átvett', slot: 'item', click: () => setPendingNegative(1) },
    { label: 'Már szerepel', slot: 'item', click: () => setPendingNegative(3) },
    { label: 'Külföldi', slot: 'item', click: () => setPendingNegative(2) },
    { label: 'Egyéb', slot: 'item', click: () => setPendingNegative(100) },
  ],
];

function negativeReasonLabel(reason: number) {
  return (reasons as Record<string, string>)[String(reason)] ?? 'Elutasítás oka';
}

async function postUrl(url: string, data: any) {
  return await $authFetch(url, data);
}

let allPersons = ref<any[]>([]);
let allInstitutions = ref<any[]>([]);
let allPlaces = ref<any[]>([]);
let kwOthers = ref<any[]>([]);
let allOthers = ref<any[]>([]);

let positivePersons = ref<any[]>([]);
let positiveInstitutions = ref<any[]>([]);
let positivePlaces = ref<any[]>([]);
let positiveOthers = ref<any[]>([]);
let positiveFiles = ref<any[]>([]);

function mapEntities(entities: any[]) {
  const entitiesMap: Record<string, any[]> = {} as any;
  for (const entity of entities) {
    const key = String(entity.db_id);
    if ((entitiesMap as any)[key])
      (entitiesMap as any)[key].push({ ...entity });
    else (entitiesMap as any)[key] = [{ ...entity }];
  }

  const mappedEntities = [];
  for (const id in (entitiesMap as any)) {
    let entityList = (entitiesMap as any)[id];
    if (id != null) {
      let entity = { ...entityList[0] };
      entity["list"] = [...entityList];
      mappedEntities.push({ ...entity });
    } else {
      for (const entity of entityList) {
        entity["list"] = [{ ...entity }];
        mappedEntities.push({ ...entity });
      }
    }
  }
  return mappedEntities.flatMap((e) => (e.db_id == null ? e.list : [e]));
}

function getKeywords(text: string) {
  function escapeRegExp(str: string) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
  }

  function findAllKeywords(text: string, keywordCandidate: any) {
    const regex = new RegExp(escapeRegExp(keywordCandidate.synonym), 'g');
    const results = [];
    let match;

    while ((match = regex.exec(text)) !== null) {
      results.push({
        etype: "keyword",
        found_name: match[0],
        found_position: match.index,
        name: keywordCandidate.name,
        db_id: keywordCandidate.db_id,
        id: keywordCandidate.db_id,
        classification_label: 0,
      });
    }

    return results;
  }

  let allKeywords: any[] = Array();
  for (const keywordCandidate of keywordSynonyms as any)
    allKeywords = allKeywords.concat(findAllKeywords(text, keywordCandidate));

  return allKeywords;
}

function openModal() {
  isOpening.value = true;
  showThanks.value = false;
  if (article.value.isDownloaded) {
    isOpen.value = true;
    isOpening.value = false;
  } else {
    $authFetch(baseUrl + "/api/article/" + article.value.id, {
      query: {},
  onResponse({ request, response, options }: any) {
        let original = article.value;
        article.value = response._data;
        article.value.original = original;
        allPersons.value = article.value.mapped_persons;
        allInstitutions.value = article.value.mapped_institutions;
        allPlaces.value = article.value.mapped_places;
        const keywords = getKeywords(article.value.text);
        kwOthers.value = mapEntities(keywords);
        allOthers.value = kwOthers.value.concat(article.value.others ?? []);
        allFiles.value = article.value.files ?? [];
        article.value.original_date = article.value.article_date;
        article.value.groupedArticles = article.value.original.groupedArticles;

        article.value.date = formatDate(article.value.date);
        article.value.article_date = formatDate(article.value.article_date);

        if (article.value.annotation_label == 1) {
          positivePersons.value = allPersons.value.filter(
            (person) =>
              (article.value.annotation_label != 1 &&
                person.classification_label == 1) ||
              (article.value.annotation_label == 1 &&
                person.annotation_label == 1)
          );
          // allPersons.value = article.value.mapped_persons
          positiveInstitutions.value = allInstitutions.value.filter(
            (institution) =>
              (article.value.annotation_label != 1 &&
                institution.classification_label == 1) ||
              (article.value.annotation_label == 1 &&
                institution.annotation_label == 1)
          );
          positivePlaces.value = allPlaces.value.filter(
            (place) =>
              ((article.value.annotation_label != 1 &&
                place.classification_label == 1) ||
                (article.value.annotation_label == 1 &&
                  place.annotation_label == 1)) &&
              place.db_id
          );
          positiveOthers.value = article.value.others.filter(
            (other: any) =>
              ((article.value.annotation_label != 1 &&
                other.classification_label == 1) ||
                (article.value.annotation_label == 1 &&
                  other.annotation_label == 1)) &&
              other.db_id
          );
          positiveFiles.value = article.value.files.filter(
            (file: any) =>
              ((article.value.annotation_label != 1 &&
                file.classification_label == 1) ||
                (article.value.annotation_label == 1 &&
                  file.annotation_label == 1)) &&
              file.db_id
          );
          console.log("positiveFiles");
          console.log(positiveFiles.value);
        }

        article.value.institutions = article.value.institutions ?? [];
        article.value.persons = article.value.persons ?? [];
        article.value.places = article.value.places ?? [];
        article.value.others = article.value.others ?? [];
        article.value.text = article.value.text ?? "";
        article.value.title = article.value.title ?? "";
        article.value.description = article.value.description ?? "";

        category.value = article.value.category;
        richText.value = getRichText();
        isOpen.value = true;
        isOpening.value = false;
        article.value.isDownloaded = true;
      },
    });
  }
}

function closeModal() {
  isOpen.value = false;
  showThanks.value = false;
}

let allFiles = ref<any[]>([]);
const {
  article: articleValue,
  allLabels,
  refresh,
  keywordSynonyms,
  is_small,
} = defineProps(["article", "allLabels", "refresh", "keywordSynonyms", "is_small"]);

const article = ref<any>(articleValue);
article.value.text = "";
article.value.institutions = [];
article.value.persons = [];
article.value.places = [];
article.value.others = [];
article.value.isDownloaded = false;

const is_active = ref(true);
let file = ref<any[]>([]);
let submitted = ref(false);
let errorText = ref("");
let articleLength = computed(() => (article.value.text ?? "").length)

async function retryArticle() {
  // TODO
}

function getMethod() {
  if (article.value.annotation_label == null)
    return "annote"
  else if (article.value.annotation_label == 1)
    return "edit"
  else if (article.value.annotation_label == 0)
    return "change"
}

async function deleteArticle() {
  await postUrl(baseUrl + "/api/annote/negative", {
    method: "POST",
    body: { id: article.value.id, reason: 0 },
  });
  refresh();
}

async function submitArticle() {
  submitted.value = true;
  showThanks.value = true;
  thanksMessage.value = getRandomThanks();

  let positivePersonsList = positivePersons.value
    .map((person) => person.occurences ?? person)
    .flat();
  positivePersonsList.forEach((element) => {
    element.annotation_label = 1;
    if (element.name == null) element.name = element.label;
  });

  let positiveInstitutionsList = positiveInstitutions.value
    .map((institution) => institution.occurences ?? institution)
    .flat();
  positiveInstitutionsList.forEach((element) => {
    element.annotation_label = 1;
    if (element.name == null) element.name = element.label;
  });

  let positivePlacesList = positivePlaces.value
    .map((place) => place.occurences ?? place)
    .flat();
  positivePlacesList.forEach((element) => {
    element.annotation_label = 1;
  });

  try {
    await $authFetch(baseUrl + "/api/" + getMethod() + "/positive", {
      method: "POST",
      body: {
        id: article.value.id,
        newspaper_id: article.value.newspaper_id,
        newspaper_name: article.value.newspaper_name,
        url: article.value.url,
        title: article.value.title,
        description: article.value.description,
        text: article.value.text,
        positive_persons: positivePersonsList,
        positive_institutions: positiveInstitutionsList,
        positive_places: positivePlacesList,
  category: Number(category.value),
        tags: positiveOthers.value,
        active: is_active.value,
        file_ids: positiveFiles.value.map((file) => file.db_id),
        pub_date: article.value.original_date,
      },
  onResponseError({ request, response, options }: any) {
        submitted.value = false;
        errorText.value = response._data.error;
      },
  onResponse({ request, response, options }: any) {
        submitted.value = false;
        if (response.status >= 300) {
          errorText.value =
            "\n" + response.status + " Hiba: " + response._data.error;
          return;
        }
        refresh();
        isOpen.value = false;
        submitted.value = false;
      },
    });
  } catch (error) {
    if (submitted.value) {
      submitted.value = false;
      console.log(error);
  errorText.value = String(error);
    }
  }
  showThanks.value = false;
}

const isOpen = ref(false);
const isOpening = ref(false);

article.value.date = formatDate(article.value.date);

function getRichText() {
  let texthtml = article.value.text ?? '';

  let allPersons = (article.value.mapped_persons as any[])
    .map((person: any) => person.occurences ?? [person])
    .flat()
    .filter((obj: any) => obj.found_position != null);
  allPersons.forEach((element: any) => {
    element.etype = "person";
  });

  console.log('allPersons');
  console.log(allPersons);

  let allInstitutions = (article.value.mapped_institutions as any[])
    .map((person: any) => person.occurences ?? [person])
    .flat()
    .filter((obj: any) => obj.found_position != null);
  allInstitutions.forEach((element: any) => {
    element.etype = "institution";
  });

  let allPlaces = (article.value.mapped_places as any[])
    .map((person: any) => person.occurences ?? [person])
    .flat()
    .filter((obj: any) => obj.found_position != null);
  allPlaces.forEach((element: any) => {
    element.etype = "place";
  });
  let allEntities = allPersons
    .concat(allInstitutions, allPlaces, kwOthers.value)
    .filter(
      (obj1, i, arr) =>
        arr.findIndex((obj2) => obj2.found_position === obj1.found_position) ===
        i || !("found_position" in obj1)
    );

  allEntities.sort(function (a, b) {
    return a.found_position - b.found_position;
  });

  let richText = "";
  let lastIndex = 0;
  for (const entity of allEntities) {
    richText += texthtml.substring(lastIndex, entity.found_position);
    if (entity.etype == "person")
      richText +=
        '<span style="color:red; font-weight:bold">' +
        entity.found_name +
        "</span>";
    else if (entity.etype == "institution")
      richText +=
        '<span style="color:blue; font-weight:bold">' +
        entity.found_name +
        "</span>";
    else if (entity.etype == "place")
      richText +=
        '<span style="color:purple; font-weight:bold">' +
        entity.found_name +
        "</span>";
    else if (entity.etype == "keyword")
      richText +=
        '<span style="background-color:#aaffaa;">' +
        entity.found_name +
        "</span>";

    lastIndex = entity.found_position + entity.found_name.length;
  }
  richText += texthtml.substring(lastIndex);

  return richText.split("\n").join("<br>");
}

const richText = ref("");

// Handle update event for positivePeople
const updatePositivePersons = (newValue: any[]) => {
  positivePersons.value = newValue;
};

// Handle update event for positiveInstitutions
const updatePositiveInstitutions = (newValue: any[]) => {
  positiveInstitutions.value = newValue;
};

// Handle update event for positivePlaces
const updatePositivePlaces = (newValue: any[]) => {
  positivePlaces.value = newValue;
};

// Handle update event for positiveTags
const updatePositiveOthers = (newValue: any[]) => {
  positiveOthers.value = newValue;
};

// Handle update event for positiveTags
const updatePositiveFiles = (newValue: any[]) => {
  positiveFiles.value = newValue;
};
</script>
