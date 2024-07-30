<template>
  <div class="p-4">
    <div class="max-w-2xl w-full rounded overflow-hidden shadow-lg mb-4 p-4">
      <p>
        <UBadge class="m-1" color="gray">
          <UTooltip
            v-if="article.skip_reason > 1"
            :text="'letöltési hiba ' + (article.mod_name ?? '')"
          >
            <Icon size="1.5em" name="mdi:alert-circle-outline" class="text-orange-500" />
          </UTooltip>
          <UTooltip
            v-else-if="article.processing_step < 4"
            :text="'feldolgozás alatt ' + (article.mod_name ?? '')"
          >
            <Icon size="1.5em" name="mdi:database-clock-outline" class="text-gray-500" />
          </UTooltip>
          <UTooltip
            v-else-if="
              article.annotation_label == null &&
              article.classification_label == 0
            "
            :text="'nem illik az adatbázisba ' + (article.mod_name ?? '')"
          >
            <Icon size="1.5em" name="mdi:window-close" class="text-gray-500" />
          </UTooltip>
          <UTooltip
            v-else-if="
              article.annotation_label == null &&
              article.classification_label == 1
            "
            :text="'ellenőrizendő ' + (article.mod_name ?? '')"
          >
            <Icon size="1.5em" name="mdi:question-mark" class="text-gray-500" />
          </UTooltip>
          <UTooltip
            v-else-if="article.annotation_label == 0"
            :text="'elutasított ' + (article.mod_name ?? '')"
          >
            <Icon size="1.5em" name="mdi:database-remove-outline" class="text-red-500" />
          </UTooltip>
          <UTooltip
            v-else-if="article.annotation_label == 1"
            :text="'elfogadott ' + (article.mod_name ?? '')"
          >
            <Icon
              size="1.5em"
              name="mdi:database-check-outline"
              class="text-green-500"
            />
          </UTooltip>
        </UBadge>
        <a :href="article.url" target="_blank" class="font-bold text-xl mb-2 ml-1">{{
          article.title
        }}</a>

      </p>
      <UBadge class="m-1" color="blue"> {{ article.newspaper_name }} </UBadge>
      <UBadge v-if="article.source == 1" class="m-1" color="orange">
        manuálisan hozzáadott
      </UBadge>
      <p class="text-base text-pretty">{{ article.description }}</p>
      <p class="text-base text-right py-1">{{ article.date }}</p>
      <UButton v-if="article.skip_reason > 1" color="grey" @click="retryArticle"
        >Újra</UButton
      >
      <UContainer
        v-else-if="
          article.processing_step >= 4 && article.classification_label != 0
        "
        class="flex justify-between px-0 sm:px-0 lg:px-0"
      >
        <UButtonGroup
          v-if="article.annotation_label != 0"
          size="sm"
          orientation="horizontal"
        >
          <UButton color="red" @click="deleteArticle">{{
            article.annotation_label == null ? "Elutasít" : "Mégis elutasít"
          }}</UButton>
          <UDropdown :items="items" :popper="{ placement: 'bottom-end' }">
            <UButton
              color="white"
              label=""
              trailing-icon="i-heroicons-chevron-down-20-solid"
            />
            <template #item="{ item }">
              <span class="">{{ item.label }}</span>
            </template>
          </UDropdown>
        </UButtonGroup>
        <UCheckbox
          v-if="article.annotation_label != 0"
          @change="selected"
          class="items-center p-2 scale-125"
          color="red"
          v-model="selection"
          name="selection"
          label=""
        />
        <UButton
          v-if="true"
          @click="openModal"
          :loading="isOpening"
          class="ml-auto"
          >{{
            article.annotation_label == null
              ? "Szerkesztés"
              : article.annotation_label == 0
              ? "Mégis elfogad"
              : "Szerkesztés"
          }}</UButton
        >
      </UContainer>
      <UButton
        v-else-if="
          article.processing_step == 4 && article.classification_label == 0
        "
        @click="forceAccept"
        class="ml-auto"
        color="purple"
        >{{ "Mégis feldolgoz" }}</UButton
      >
    </div>
    <UModal v-model="isOpen" :ui="{ width: 'sm:max-w-7xl' }">
      <div class="p-4 w-full">
        <div class="my-2 flex justify-center px-0 sm:px-0 lg:px-0 flex-wrap">
          <div class="max-w-2xl mx-4 flex-grow">
            <p>Cím:</p>
            <UTextarea
              class="my-2 min-h-0"
              rows="1"
              autoresize
              v-model="article.title"
            />
            <p>URL:</p>
            <UInput class="my-2" v-model="article.url" />
            <p>Leírás:</p>
            <UTextarea class="my-2" resize v-model="article.description" />
            <div class="flex justify-between">
              <p>Szöveg:</p>
              <div class="flex items-center">
                <p>szerkeszt:</p>
                <UToggle class="m-2" size="md" color="primary" v-model="edit" />
              </div>
            </div>
            <UTextarea
              v-if="edit"
              class="my-2"
              v-model="article.text"
              rows="20"
            />
            <div v-if="!edit" style="overflow-y: scroll; height: 400px">
              <span class="my-2" v-html="richText"></span>
            </div>
          </div>

          <div class="max-w-lg mx-4 flex-grow">
            <SelectMenu
              :list="allPersons"
              type="személy"
              :creatable="true"
              :positive-list="positivePersons"
              @update:positiveList="updatePositivePersons"
              :labels="allLabels['person']"
            />
            <SelectMenu
              :list="allInstitutions"
              type="intézmény"
              :creatable="true"
              :positive-list="positiveInstitutions"
              @update:positiveList="updatePositiveInstitutions"
              :labels="allLabels['institution']"
            />
            <SelectMenu
              :list="allPlaces"
              type="helyszín"
              :creatable="false"
              :positive-list="positivePlaces"
              @update:positiveList="updatePositivePlaces"
              :labels="allLabels['place']"
            />
            <SelectMenu
              :list="allOthers"
              type="egyéb"
              :creatable="false"
              :positive-list="positiveOthers"
              @update:positiveList="updatePositiveOthers"
              :labels="allLabels['keywords']"
            />
            <p>Kategória:</p>
            <USelect
              v-model="category"
              :options="categories"
              option-attribute="name"
              value-attribute="id"
            />
            <p>Akta:</p>
            <USelectMenu
              searchable
              multiple
              :search-attributes="['name']"
              searchable-placeholder="Keresés..."
              clear-search-on-close
              v-model="file"
              :options="allFiles"
              option-attribute="name"
              value-attribute="id"
            >
              <template #empty> betöltés... </template>
              <template #label>
                <span>{{
                  allFiles
                    .filter((item) => file.includes(item.id))
                    .map((item) => item.name)
                    .join(", ") || "semmi"
                }}</span>
              </template>
            </USelectMenu>
            <p>publikálás: {{ article.article_date }}</p>
            <p>{{ errorText }}</p>
            <UButton
              class="my-5"
              v-if="article.annotation_label == 1"
              target="_blank"
              :to="`https://autokmdb.deepdata.hu/admin.php?mod=news&action=news&do=news&news_id=${article.news_id}`"
            >
              szerkesztés az adminban
            </UButton>
          </div>
        </div>
        <UContainer class="my-2 flex justify-between px-0 sm:px-0 lg:px-0">
          <UButton color="gray" @click="closeModal">Mégse</UButton>

          <div class="my-2 flex justify-between">
            <UButtonGroup
              v-if="article.annotation_label != 0"
              size="sm"
              orientation="horizontal"
            >
              <UButton color="red" @click="deleteArticle">{{
                article.annotation_label == null ? "Elutasít" : "Mégis elutasít"
              }}</UButton>
              <UDropdown :items="items" :popper="{ placement: 'bottom-end' }">
                <UButton
                  color="white"
                  label=""
                  trailing-icon="i-heroicons-chevron-down-20-solid"
                />
                <template #item="{ item }">
                  <span class="">{{ item.label }}</span>
                </template>
              </UDropdown>
            </UButtonGroup>
            <UCheckbox
              class="mx-5"
              size="xl"
              v-model="is_active"
              label="Aktív"
            />
            <UButton @click="submitArticle" :loading="submitted"
              >Elfogad</UButton
            >
          </div>
        </UContainer>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const config = useRuntimeConfig();
const baseUrl = config.public.baseUrl;

const edit = ref(false);
const selection = ref(false);
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
function selected() {
  console.log("selected " + selection.value);
  article.value.selected = selection.value;
  if (article.value.original) article.value.original.selected = selection.value;
}

const items = [
  [
    {
      label: "Átvett",
      slot: "item",
      click: async () => {
        await postUrl(baseUrl + "/api/annote/negative", {
          method: "POST",
          body: { id: article.value.id, reason: 1 },
        });
        refresh();
      },
    },
    {
      label: "Már szerepel",
      slot: "item",
      click: async () => {
        await postUrl(baseUrl + "/api/annote/negative", {
          method: "POST",
          body: { id: article.value.id, reason: 3 },
        });
        refresh();
      },
    },
    {
      label: "Külföldi",
      slot: "item",
      click: async () => {
        await postUrl(baseUrl + "/api/annote/negative", {
          method: "POST",
          body: { id: article.value.id, reason: 2 },
        });
        refresh();
      },
    },
    {
      label: "Egyéb",
      slot: "item",
      click: async () => {
        await postUrl(baseUrl + "/api/annote/negative", {
          method: "POST",
          body: { id: article.value.id, reason: 100 },
        });
        refresh();
      },
    },
  ],
];

async function postUrl(url, data) {
  return await $fetch(url, data);
}

let allPersons = ref([]);
let allInstitutions = ref([]);
let allPlaces = ref([]);
let allOthers = ref([]);

let positivePersons = ref([]);
let positiveInstitutions = ref([]);
let positivePlaces = ref([]);
let positiveOthers = ref([]);

function mapEntities(entities) {
  const entitiesMap = {};
  for (const entity of entities) {
    if (entitiesMap[entity.db_id])
      entitiesMap[entity.db_id].push({ ...entity });
    else entitiesMap[entity.db_id] = [{ ...entity }];
  }

  const mappedEntities = [];
  for (const id in entitiesMap) {
    let entityList = entitiesMap[id];
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

function getKeywords(text) {
  function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
  }

  function findAllKeywords(text, keywordCandidate) {
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

  let allKeywords = Array();
  for (const keywordCandidate of keywordSynonyms)
    allKeywords = allKeywords.concat(findAllKeywords(text, keywordCandidate)); 

  return allKeywords;
}

function openModal() {
  isOpening.value = true;
  if (article.value.isDownloaded) {
    isOpen.value = true;
    isOpening.value = false;
  } else {
    $fetch(baseUrl + "/api/article/" + article.value.id, {
      query: {},
      onResponse({ request, response, options }) {
        let original = article.value;
        article.value = response._data;
        article.value.original = original;
        allPersons.value = mapEntities(article.value.persons).filter(
          (obj1, i, arr) =>
            arr.findIndex((obj2) => obj2.name === obj1.name) === i ||
            !("name" in obj1)
        );
        allInstitutions.value = mapEntities(article.value.institutions).filter(
          (obj1, i, arr) =>
            arr.findIndex((obj2) => obj2.name === obj1.name) === i ||
            !("name" in obj1)
        );
        allPlaces.value = mapEntities(article.value.places);
        const keywords = getKeywords(article.value.text);
        allOthers.value = mapEntities(keywords);
        article.value.original_date = article.value.article_date;

        article.value.date = new Date(
          Date.parse(article.value.date)
        ).toLocaleString();
        article.value.article_date = new Date(
          Date.parse(article.value.article_date)
        ).toLocaleString();

        if (article.value.annotation_label == 1) {
          positivePersons.value = allPersons.value.filter(
            (person) =>
              (article.value.annotation_label != 1 &&
                person.classification_label == 1) ||
              (article.value.annotation_label == 1 &&
                person.annotation_label == 1)
          );
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
            (other) =>
              ((article.value.annotation_label != 1 &&
                other.classification_label == 1) ||
                (article.value.annotation_label == 1 &&
                  other.annotation_label == 1)) &&
              other.db_id
          );
        }

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
}

const {
  article: articleValue,
  allLabels,
  allFiles,
  refresh,
  keywordSynonyms,
} = defineProps(["article", "allLabels", "allFiles", "refresh", "keywordSynonyms"]);
const article = ref(articleValue);
article.value.text = "";
article.value.institutions = [];
article.value.persons = [];
article.value.places = [];
article.value.others = [];
article.value.isDownloaded = false;

const is_active = ref(true);
let file = ref([]);
let submitted = ref(false);
let errorText = ref("");

async function retryArticle() {
  // TODO
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

  let positivePersonsList = positivePersons.value
    .map((person) => person.list ?? person)
    .flat();
  positivePersonsList.forEach((element) => {
    element.annotation_label = 1;
    if (element.name == null) element.name = element.label;
  });

  let positiveInstitutionsList = positiveInstitutions.value
    .map((institution) => institution.list ?? institution)
    .flat();
  positiveInstitutionsList.forEach((element) => {
    element.annotation_label = 1;
    if (element.name == null) element.name = element.label;
  });

  let positivePlacesList = positivePlaces.value
    .map((place) => place.list ?? place)
    .flat();
  positivePlacesList.forEach((element) => {
    element.annotation_label = 1;
  });

  try {
    await postUrl(baseUrl + "/api/annote/positive", {
      method: "POST",
      body: {
        id: article.value.id,
        newspaper_id: article.value.newspaper_id,
        url: article.value.url,
        title: article.value.title,
        description: article.value.description,
        text: article.value.text,
        positive_persons: positivePersonsList,
        positive_institutions: positiveInstitutions.value,
        positive_places: positivePlaces.value,
        category: parseInt(category.value),
        tags: positiveOthers.value,
        active: is_active.value,
        file_ids: file.value,
        pub_date: article.value.original_date,
      },

      onResponse({ request, response, options }) {
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
    submitted.value = false;
    console.log(error);
    errorText.value = error;
  }
}
const isOpen = ref(false);
const isOpening = ref(false);

article.value.date = new Date(Date.parse(article.value.date)).toLocaleString();
// article.value.article_date = new Date(Date.parse(article.value.article_date)).toLocaleString()

function getRichText() {
  let texthtml = article.value.text;

  let allPersons = article.value.persons
    .filter((obj) => obj.found_position)
    .map((person) => person.list ?? [person])
    .flat();
  allPersons.forEach((element) => {
    element.etype = "person";
  });

  let allInstitutions = article.value.institutions
    .filter((obj) => obj.found_position)
    .map((person) => person.list ?? [person])
    .flat();
  allInstitutions.forEach((element) => {
    element.etype = "institution";
  });

  let allPlaces = article.value.places
    .filter((obj) => obj.found_position)
    .map((person) => person.list ?? [person])
    .flat();
  allPlaces.forEach((element) => {
    element.etype = "place";
  });
  let allEntities = allPersons
    .concat(allInstitutions, allPlaces, allOthers.value)
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
const updatePositivePersons = (newValue) => {
  positivePersons.value = newValue;
};

// Handle update event for positiveInstitutions
const updatePositiveInstitutions = (newValue) => {
  positiveInstitutions.value = newValue;
};

// Handle update event for positivePlaces
const updatePositivePlaces = (newValue) => {
  positivePlaces.value = newValue;
};

// Handle update event for positiveTags
const updatePositiveOthers = (newValue) => {
  positiveOthers.value = newValue;
};
</script>
