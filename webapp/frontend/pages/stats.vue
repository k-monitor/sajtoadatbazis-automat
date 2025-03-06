<template>
  <div class="container">
    <div class="controls">
      <div class="summary" v-if="filteredData.length > 0">
        <div style="color: #666; margin-bottom: 8px">
          Átlagosan <br />
          {{ filteredData[0].date }} -
          {{ filteredData[filteredData.length - 1].date }}
        </div>
        <div>
          <div
            class="square"
            :style="{ background: chartColors.positive.background }"
          >
            {{ getCount("positive") }}%
          </div>
          Elfogadott cikkek
        </div>
        <div>
          <div
            class="square"
            :style="{ background: chartColors.todo.background }"
          >
            {{ getCount("todo") }}%
          </div>
          Kezeletlen cikkek
        </div>
        <div>
          <div
            class="square"
            :style="{ background: chartColors.negative.background }"
          >
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
import { chartOptions, chartColors } from "../config/chart";
import { useDateRange } from "../composables/useDateRange";
import type { DataRow } from "../types.ts";
import DateRangeSlider from "../components/DateRangeSlider.vue";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const data = ref<DataRow[]>([]);
const { startDateIndex, endDateIndex, filteredData, updateDateRange } =
  useDateRange(data);

onMounted(async () => {
  const config = useRuntimeConfig();
  const response = await fetch(
    config.public.baseUrl + "/api/articles_by_day.csv"
  );
  const csv = await response.text();
  const result = parse<DataRow>(csv, { header: true, skipEmptyLines: true });
  console.log(result.data);

  data.value = result.data;
  startDateIndex.value = 0;
  endDateIndex.value = data.value.length;
  updateDateRange();
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
</style>
