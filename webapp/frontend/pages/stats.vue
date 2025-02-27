<template>
  <div class="container">
    <div class="controls"></div>
    <div>
      <Bar
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
        v-model:startIndex="startDateIndex"
        v-model:endIndex="endDateIndex"
        :max="data.length - 1"
        :startDate="data[startDateIndex]?.date"
        :endDate="data[endDateIndex]?.date"
        @update="updateDateRange"
      />
    </div>
  </div>
</template>

<script setup>
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
import DateRangeSlider from "../components/DateRangeSlider.vue";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const data = ref([]);
const { startDateIndex, endDateIndex, filteredData, updateDateRange } =
  useDateRange(data);

onMounted(async () => {
  const response = await fetch("/data.csv");
  const csv = await response.text();
  const result = parse(csv, { header: true });
  data.value = result.data;
  startDateIndex.value = 0;
  endDateIndex.value = data.value.length - 1;
});
</script>
