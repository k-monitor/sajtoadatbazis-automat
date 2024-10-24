<template>
  <div>
    <p  class="font-bold" style="text-transform: capitalize">{{ type }}:</p>
    <USelectMenu
      @close="() => $emit('update:positiveList', localPositiveList)"
      :searchable="search"
      searchable-placeholder="Keresés..."
      class="my-2"
      v-model="localPositiveList"
      :options="list"
      option-attribute="label"
      show-create-option-when="always"
      :creatable="creatable"
      multiple
      v-model:query="query"
      @update:model-value="handleUpdate"
      @keyup="onPress"
    >
      <template #label>
        <span v-if="localPositiveList.length">{{
          localPositiveList
            .map((item) =>
              item.db_name != null && item.db_name
                ? item.db_name
                : item.name != null
                ? item.name
                : item.label
            )
            .join(", ")
        }}</span>
        <span v-else>Válassz ki elemeket</span>
      </template>
      <template #option-create="{ option }">
        <span class="flex-shrink-0">Új {{ type }}:</span>
        <span class="block truncate">{{ option.label }}</span>
      </template>
      <template #option="{ option }">
        <span class="block truncate">
          <Icon v-if="option.db_id" name="mdi:database-outline" class="text-green-500" />
          {{
            option.db_name != null
              ? option.db_name
              : option.name != null
              ? option.name
              : option.label
          }}
          {{
            option.classification_score != null
              ? "(" + (option.classification_score * 100).toFixed(0) + "%"
              : ""
          }}
          <Icon
            v-if="
              option.classification_label == 1 &&
              option.classification_score != null
            "
            name="mdi:emoticon-devil"
            class="text-red-500"
          />
          <Icon
            v-else-if="option.classification_score != null"
            name="mdi:account-cowboy-hat"
            class="text-yellow-500"
          />
          {{ option.classification_score != null ? ")" : "" }}
        </span>
      </template>
      <template #empty> Nincs {{ type }} </template>
    </USelectMenu>
  </div>
</template>

<script setup lang="ts">
const handleUpdate = (event) => {
  query.value = "";
};

import { distance } from "fastest-levenshtein";

const onPress = (e) => {
  if (e.keyCode <= 64) // don't do anything if tab/enter/etc is pressed
    return;
  e.target.click(); // open the select menu by clicking the focused button
  query.value = e.key; // add the pressed key to the search query
};

function search(q: string) {
  if (q === "") {
    return list
      .concat(localPositiveList.value)
      .filter(
        (obj1, i, arr) =>
          arr.findIndex((obj2) => obj2.id === obj1.id) === i ||
          !("found_name" in obj1)
      )
      .filter(
        (obj1, i, arr) =>
          arr.findIndex((obj2) => obj2.db_id === obj1.db_id) === i ||
          !("db_id" in obj1)
      );
  }

  return list
    .concat(localPositiveList.value)
    .filter(
      (obj1, i, arr) =>
        arr.findIndex((obj2) => obj2.id === obj1.id) === i ||
        !("found_name" in obj1)
    )
    .concat(
      labels
        .filter((item: any) => {
          return (
            item.name != null &&
            item.name.toLowerCase().includes(q.toLowerCase())
          );
        })
        .sort(function (a, b) {
          return (
            distance(a.name.toLowerCase(), q.toLowerCase()) -
            distance(b.name.toLowerCase(), q.toLowerCase())
          );
        })
        .slice(0, 5)
        .map((item: any) => {
          return {
            id: "db_" + item.id,
            db_id: item.id,
            name: item.name,
            db_name: item.name,
          };
        })
    )
    .filter(
      (obj1, i, arr) =>
        arr.findIndex((obj2) => obj2.db_id === obj1.db_id) === i ||
        !("db_id" in obj1)
    )
    .filter(
      (obj1, i, arr) =>
        arr.findIndex((obj2) => obj2.name === obj1.name) === i ||
        !("name" in obj1)
    )
    .filter((item: any) => {
      return (
        item.name != null && item.name.toLowerCase().includes(q.toLowerCase())
      );
    })
    .slice(0, 5);
}

const { list, creatable, positiveList, labels, type } = defineProps([
  "list",
  "creatable",
  "positiveList",
  "labels",
  "type",
]);
const query = ref("");
// Local state
const localPositiveList = ref(positiveList);
console.log("localPositiveList.value");
console.log(localPositiveList.value);
</script>
