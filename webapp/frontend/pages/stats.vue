<template>
  <div class="container">
    <div class="controls">
      <div class="filter-section">
        <label for="domain-select">Hírportál:</label>
        <select
          id="domain-select"
          v-model="selectedDomainId"
          @change="fetchData"
          class="domain-select"
        >
          <option value="">Összes hírportál</option>
          <option v-for="domain in domains" :key="domain.id" :value="domain.id">
            {{ domain.name }}
          </option>
        </select>
      </div>
      <DateRangeSelector
        class="m-1"
        :selected="selected"
        :ranges="ranges"
        @update:selected="updateSelectedDateRange"
        @refresh="refresh"
      />
      <div class="summary" v-if="filteredData.length > 0">
        <div style="color: #666; margin-bottom: 8px">
          Átlagosan <br />
          {{ filteredData[0].date }} -
          {{ filteredData[filteredData.length - 1].date }}
        </div>
        <div>
          <div class="square" :style="{ background: chartColors.positive.background }">
            {{ getCount("positive") }}%
          </div>
          Elfogadott cikkek
        </div>
        <div>
          <div class="square" :style="{ background: chartColors.todo.background }">
            {{ getCount("todo") }}%
          </div>
          Kezeletlen cikkek
        </div>
        <div>
          <div class="square" :style="{ background: chartColors.negative.background }">
            {{ getCount("negative") }}%
          </div>
          Elutasított cikkek
        </div>
      </div>
    </div>
    <div class="graph">
      <Bar
        v-if="data.length > 0"
        :data="{
          labels: filteredData.map((row) => row.date),
          datasets: [
            {
              label: 'Elfogadott cikkek',
              data: filteredData.map((row) => row.count_positive),
              backgroundColor: chartColors.positive.background,
              borderColor: chartColors.positive.border,
            },
            {
              label: 'Kezeletlen cikkek',
              data: filteredData.map((row) => row.count_todo),
              backgroundColor: chartColors.todo.background,
              borderColor: chartColors.todo.border,
            },
            {
              label: 'Elutasított cikkek',
              data: filteredData.map((row) => row.count_negative),
              backgroundColor: chartColors.negative.background,
              borderColor: chartColors.negative.border,
            },
          ],
        }"
        :options="chartOptions"
      />
      <DateRangeSlider
        v-if="data.length > 0"
        v-model:startIndex="startDateIndex"
        v-model:endIndex="endDateIndex"
        :max="data.length"
        :startDate="data[startDateIndex]?.date"
        :endDate="data[endDateIndex]?.date"
        @update="updateDateRange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Bar } from "vue-chartjs";
import { parse } from "papaparse";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import type { ChartOptions } from "chart.js";
import { chartOptions, chartColors } from "../config/chart";
import { useDateRange } from "../composables/useDateRange";
import type { DataRow } from "../types.ts";
import DateRangeSlider from "../components/DateRangeSlider.vue";
import { sub, format } from "date-fns";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const data = ref<DataRow[]>([]);
const domains = ref<Array<{ id: number; name: string }>>([]);
const selectedDomainId = ref<string>("");
const { startDateIndex, endDateIndex, filteredData, updateDateRange } = useDateRange(
  data
);
const selected = ref({ start: sub(new Date(), { days: 14 }), end: new Date() });

const ranges = [
  { label: "Elmúlt 1 nap", duration: { days: 1 - 1 } },
  { label: "Elmúlt 2 nap", duration: { days: 2 - 1 } },
  { label: "Elmúlt 7 nap", duration: { days: 7 - 1 } },
  { label: "Elmúlt 2 hét", duration: { days: 14 - 1 } },
  { label: "Elmúlt 1 hónap", duration: { days: 30 - 1 } },
  { label: "Elmúlt 3 hónap", duration: { months: 3 } },
  { label: "Elmúlt 6 hónap", duration: { months: 6 } },
  { label: "Elmúlt 1 év", duration: { years: 1 } },
  { label: "Elmúlt 3 év", duration: { years: 3 } },
];

function updateSelectedDateRange(newRange) {
  selected.value = newRange;

  // Find the start and end indices based on the selected date range
  const startDate = format(newRange.start, "yyyy-MM-dd");
  const endDate = format(newRange.end, "yyyy-MM-dd");

  const startIndex = data.value.findIndex((row) => row.date >= startDate);
  const endIndex = data.value.findIndex((row) => row.date > endDate);

  startDateIndex.value = startIndex !== -1 ? startIndex : 0;
  endDateIndex.value = endIndex !== -1 ? endIndex : data.value.length;

  console.log("Selected date range updated:", {
    start: newRange.start,
    end: newRange.end,
    startIndex: startDateIndex.value,
    endIndex: endDateIndex.value,
  });

  updateDateRange();
}

function refresh() {
  console.log("refresh");
}

const fetchData = async () => {
  const config = useRuntimeConfig();
  const params = new URLSearchParams();
  if (selectedDomainId.value) {
    params.append("newspaper_id", selectedDomainId.value);
  }

  const url = `${config.public.baseUrl}/api/articles_by_day.csv${
    params.toString() ? "?" + params.toString() : ""
  }`;
  const response = await fetch(url);
  const csv = await response.text();
  const result = parse<DataRow>(csv, { header: true, skipEmptyLines: true });

  data.value = result.data;
  startDateIndex.value = 0;
  endDateIndex.value = data.value.length;
  updateDateRange();
};

onMounted(async () => {
  const config = useRuntimeConfig();

  // Fetch domains
  const domainsResponse = await fetch(`${config.public.baseUrl}/api/domains`);
  const domainsData = await domainsResponse.json();
  domains.value = domainsData.domains;

  // Initial data fetch
  await fetchData();
});

const getCount = (type: "positive" | "todo" | "negative"): number => {
  const total = filteredData.value.reduce((sum, row) => {
    return sum + Number(row.total_count);
  }, 0);

  const typeCount = filteredData.value.reduce(
    (sum, row) => sum + Number(row[`count_${type}`]),
    0
  );
  return total > 0 ? Math.round((typeCount / total) * 100) : 0;
};
</script>

<style scoped>
.container {
  display: flex;
  width: 100%;
  flex-direction: row;
}
.controls {
  width: 300px;
}
.summary {
  font-weight: bold;
  background-color: #f3f4f6;
  border-radius: 16px;
  padding: 8px;
  margin: 8px;
}
.summary > div {
  margin: 4px;
}
.square {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  margin-right: 8px;
  border-radius: 12px;
  color: white;
}
.graph {
  flex-grow: 1;
}
.filter-section {
  margin: 8px;
  margin-bottom: 16px;
}

.filter-section label {
  display: block;
  margin-bottom: 4px;
  font-weight: bold;
}

.domain-select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background-color: white;
}
</style>
