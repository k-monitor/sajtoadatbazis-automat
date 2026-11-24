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
      <div class="filter-section">
        <label for="aggregation-select">Megjelenítés:</label>
        <select
          id="aggregation-select"
          v-model="aggregationType"
          @change="onAggregationChange"
          class="domain-select"
        >
          <option value="days">Napok</option>
          <option value="weeks">Hetek</option>
        </select>
      </div>
      <DateRangeSelector
        class="m-1"
        :selected="selected"
        :ranges="ranges"
        @update:selected="updateSelectedDateRange"
        @refresh="refresh"
      />
      <div class="summary" v-if="displayData.length > 0">
        <div style="color: #666; margin-bottom: 8px">
          Átlagosan <br />
          {{ displayData[0].date }} -
          {{ displayData[displayData.length - 1].date }}
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
        <div class="negative-breakdown">
          <div class="breakdown-item">Nem releváns: {{ getCount("negative_0") }}%</div>
          <div class="breakdown-item">Átvett: {{ getCount("negative_1") }}%</div>
          <div class="breakdown-item">Külföldi: {{ getCount("negative_2") }}%</div>
          <div class="breakdown-item">Már szerepel: {{ getCount("negative_3") }}%</div>
          <div class="breakdown-item">Egyéb: {{ getCount("negative_100") }}%</div>
        </div>
      </div>
    </div>
    <div class="graph">
      <Bar
        v-if="data.length > 0"
        :data="{
          labels: displayData.map((row) => row.date),
          datasets: [
            {
              label: 'Elfogadott cikkek',
              data: displayData.map((row) => row.count_positive),
              backgroundColor: chartColors.positive.background,
              borderColor: chartColors.positive.border,
            },
            {
              label: 'Kezeletlen cikkek',
              data: displayData.map((row) => row.count_todo),
              backgroundColor: chartColors.todo.background,
              borderColor: chartColors.todo.border,
            },
            {
              label: 'Nem releváns',
              data: displayData.map((row) => row.count_negative_0),
              backgroundColor: '#ef4444',
              borderColor: '#dc2626',
            },
            {
              label: 'Átvett',
              data: displayData.map((row) => row.count_negative_1),
              backgroundColor: '#f97316',
              borderColor: '#ea580c',
            },
            {
              label: 'Külföldi',
              data: displayData.map((row) => row.count_negative_2),
              backgroundColor: '#eab308',
              borderColor: '#ca8a04',
            },
            {
              label: 'Már szerepel',
              data: displayData.map((row) => row.count_negative_3),
              backgroundColor: '#FFEB3B',
              borderColor: '#7c3aed',
            },
            {
              label: 'Egyéb',
              data: displayData.map((row) => row.count_negative_100),
              backgroundColor: '#6b7280',
              borderColor: '#4b5563',
            },
          ],
        }"
        :options="chartOptionsWithClick"
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
import { ref, onMounted, computed } from "vue";
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
import type { DataRow } from "../types";
import DateRangeSlider from "../components/DateRangeSlider.vue";
import { sub, format, startOfWeek, addWeeks } from "date-fns";

interface DateRangeSelection {
  start: Date;
  end: Date;
}

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const data = ref<DataRow[]>([]);
const domains = ref<Array<{ id: number; name: string }>>([]);
const selectedDomainId = ref<string>("");
const aggregationType = ref<"days" | "weeks">("days");
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

function updateSelectedDateRange(newRange: DateRangeSelection) {
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

const weeklyData = computed(() => {
  if (aggregationType.value !== "weeks" || filteredData.value.length === 0) {
    return [];
  }

  const weekMap = new Map();
  
  filteredData.value.forEach(row => {
    const date = new Date(row.date);
    const weekStart = startOfWeek(date, { weekStartsOn: 1 }); // Monday as start
    const weekKey = format(weekStart, "yyyy-MM-dd");
    
    if (!weekMap.has(weekKey)) {
      weekMap.set(weekKey, {
        date: weekKey,
        count_positive: 0,
        count_todo: 0,
        count_negative: 0,
        count_negative_0: 0,
        count_negative_1: 0,
        count_negative_2: 0,
        count_negative_3: 0,
        count_negative_100: 0,
        total_count: 0
      });
    }
    
    const week = weekMap.get(weekKey);
    week.count_positive += Number(row.count_positive) || 0;
    week.count_todo += Number(row.count_todo) || 0;
    week.count_negative += Number(row.count_negative) || 0;
    week.count_negative_0 += Number(row.count_negative_0) || 0;
    week.count_negative_1 += Number(row.count_negative_1) || 0;
    week.count_negative_2 += Number(row.count_negative_2) || 0;
    week.count_negative_3 += Number(row.count_negative_3) || 0;
    week.count_negative_100 += Number(row.count_negative_100) || 0;
    week.total_count += Number(row.total_count) || 0;
  });
  
  return Array.from(weekMap.values()).sort((a, b) => a.date.localeCompare(b.date));
});

const displayData = computed(() => {
  return aggregationType.value === "weeks" ? weeklyData.value : filteredData.value;
});

const chartOptionsWithClick = computed(() => {
  return {
    ...chartOptions,
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0) {
        const clickedIndex = elements[0].index;
        const clickedDate = displayData.value[clickedIndex]?.date;
        
        if (clickedDate) {
          handleColumnClick(clickedDate);
        }
      }
    },
    plugins: {
      ...chartOptions.plugins,
      tooltip: {
        ...chartOptions.plugins?.tooltip,
        callbacks: {
          afterTitle: () => 'Kattintson a szűréshez'
        }
      }
    }
  };
});

function handleColumnClick(clickedDate: string) {
  const clickedDateObj = new Date(clickedDate);
  
  if (aggregationType.value === "weeks") {
    // For weekly view, filter to the entire week
    const weekStart = startOfWeek(clickedDateObj, { weekStartsOn: 1 });
    const weekEnd = addWeeks(weekStart, 1);
    weekEnd.setDate(weekEnd.getDate() - 1); // End of the week
    window.location = `/?dateFrom=${format(weekStart, "yyyy-MM-dd")}&dateTo=${format(weekEnd, "yyyy-MM-dd")}`;
  } else {
    window.location = `/?dateFrom=${format(clickedDateObj, "yyyy-MM-dd")}&dateTo=${format(clickedDateObj, "yyyy-MM-dd")}`;
  }
  
  updateSelectedDateRange(selected.value);
}

function onAggregationChange() {
  updateDateRange();
}

const getCount = (type: "positive" | "todo" | "negative" | "negative_0" | "negative_1" | "negative_2" | "negative_3" | "negative_100"): number => {
  const total = displayData.value.reduce((sum, row) => {
    return sum + Number(row.total_count);
  }, 0);

  const typeCount = displayData.value.reduce(
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

.graph canvas {
  cursor: pointer;
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

.negative-breakdown {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
  font-size: 0.9em;
  color: #4b5563;
}

.breakdown-item {
  margin: 2px 0;
}
</style>
